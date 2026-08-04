/* Defect Board — Jira Integration */

const AUTO_REFRESH_INTERVAL = 120000; // 2 minutes
let overviewData = null;
let sysfuncData = null;
let defectListData = null;
let selectedCategory = null;
let selectedSysfunc = null;
let currentPage = 1;
let statusDonutChart = null;
let moduleBarChart = null;
let _lastFetchTime = Date.now();
let _lastActiveTime = Date.now();

const JIRA_BASE = "https://mercedes-benz.atlassian.net";

function getFilters() {
    return {
        release: document.getElementById("filter-release")?.value || "",
        release_candidate: document.getElementById("filter-candidate")?.value || "",
        safety_type: document.getElementById("filter-safety")?.value || "",
    };
}

function buildQueryString(extra = {}) {
    const f = getFilters();
    const params = new URLSearchParams();
    if (f.release) params.set("release", f.release);
    if (f.release_candidate) params.set("release_candidate", f.release_candidate);
    if (f.safety_type) params.set("safety_type", f.safety_type);
    for (const [k, v] of Object.entries(extra)) {
        if (v) params.set(k, v);
    }
    const qs = params.toString();
    return qs ? `?${qs}` : "";
}

function showLoading(show) {
    document.getElementById("defect-loading").style.display = show ? "flex" : "none";
}

function showError(show, msg = "") {
    const el = document.getElementById("defect-error");
    el.style.display = show ? "flex" : "none";
    if (msg) document.getElementById("error-text").textContent = msg;
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// --- Load Overview ---
async function loadOverview() {
    try {
        const res = await fetch(`/api/jira/overview${buildQueryString()}`);
        if (!res.ok) throw new Error(await res.text());
        overviewData = await res.json();
        renderOverview();
    } catch (e) {
        console.error("Overview error:", e);
        showError(true, `Failed to load overview: ${e.message}`);
    }
}

function renderOverview() {
    if (!overviewData) return;
    document.getElementById("stat-total").textContent = overviewData.total;
    document.getElementById("stat-ongoing").textContent = overviewData.ongoing_count;
    document.getElementById("stat-closed").textContent = overviewData.closed_count;

    renderStatusDonut(overviewData.status_distribution || []);
}

function renderStatusDonut(statusDist) {
    const ctx = document.getElementById("status-donut-chart");
    if (!ctx) return;

    if (statusDonutChart) statusDonutChart.destroy();

    const labels = statusDist.map(s => s.status);
    const data = statusDist.map(s => s.count);
    const colors = statusDist.map(s => s.color);

    statusDonutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: colors,
                borderWidth: 0,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "65%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#ccc",
                        font: { size: 11 },
                        padding: 12,
                        usePointStyle: true,
                        pointStyle: "circle",
                    }
                },
                tooltip: {
                    backgroundColor: "#1a1a1a",
                    titleColor: "#fff",
                    bodyColor: "#ccc",
                    borderColor: "#333",
                    borderWidth: 1,
                }
            }
        },
        plugins: [{
            id: "centerText",
            beforeDraw(chart) {
                const { width, height, ctx: c } = chart;
                c.save();
                const total = data.reduce((a, b) => a + b, 0);
                c.font = "bold 22px Segoe UI";
                c.fillStyle = "#ffffff";
                c.textAlign = "center";
                c.textBaseline = "middle";
                c.fillText(total, width / 2, height / 2 - 8);
                c.font = "11px Segoe UI";
                c.fillStyle = "#888";
                c.fillText("Ongoing", width / 2, height / 2 + 12);
                c.restore();
            }
        }]
    });
}

// --- Load SysFunc ---
async function loadSysfunc() {
    try {
        const res = await fetch(`/api/jira/by-sysfunc${buildQueryString()}`);
        if (!res.ok) throw new Error(await res.text());
        sysfuncData = await res.json();
        renderCategoryTabs();
        renderSysfuncTable();
        renderModuleBarChart();
    } catch (e) {
        console.error("Sysfunc error:", e);
    }
}

function renderCategoryTabs() {
    const container = document.getElementById("category-tabs");
    if (!container || !sysfuncData) return;

    const categories = sysfuncData.categories || [];
    const sysfuncs = sysfuncData.sysfuncs || [];

    let html = `<button class="cat-tab ${!selectedCategory ? 'active' : ''}" onclick="selectCategory(null)">All (${sysfuncs.reduce((a, s) => a + s.open_count, 0)})</button>`;
    categories.forEach(cat => {
        const count = sysfuncs.filter(s => s.category === cat).reduce((a, s) => a + s.open_count, 0);
        html += `<button class="cat-tab ${selectedCategory === cat ? 'active' : ''}" onclick="selectCategory('${cat}')">${escapeHtml(cat)} (${count})</button>`;
    });
    container.innerHTML = html;
}

function selectCategory(cat) {
    selectedCategory = cat;
    selectedSysfunc = null;
    currentPage = 1;
    renderCategoryTabs();
    renderSysfuncTable();
    loadDefectList();
}

function renderSysfuncTable() {
    const tbody = document.getElementById("sysfunc-body");
    const subtitle = document.getElementById("sysfunc-subtitle");
    if (!tbody || !sysfuncData) return;

    let sysfuncs = sysfuncData.sysfuncs || [];
    if (selectedCategory) {
        sysfuncs = sysfuncs.filter(s => s.category === selectedCategory);
        subtitle.textContent = selectedCategory;
    } else {
        subtitle.textContent = "All categories";
    }

    if (sysfuncs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="no-data">No system functions in this category</td></tr>`;
        return;
    }

    tbody.innerHTML = sysfuncs.map(s => `
        <tr class="sysfunc-row ${selectedSysfunc === s.acronym ? 'selected' : ''}" onclick="selectSysfunc('${s.acronym}')">
            <td class="acronym-cell">${escapeHtml(s.acronym)}</td>
            <td>${escapeHtml(s.name)}</td>
            <td class="tester-cell">${escapeHtml(s.tester || "")}</td>
            <td><span class="count-badge badge-ongoing">${s.open_count}</span></td>
            <td><span class="count-badge badge-closed">${s.closed_count}</span></td>
            <td><span class="count-badge badge-total">${s.total}</span></td>
        </tr>
    `).join("");
}

function selectSysfunc(acronym) {
    if (selectedSysfunc === acronym) {
        selectedSysfunc = null;
    } else {
        selectedSysfunc = acronym;
    }
    currentPage = 1;
    renderSysfuncTable();
    loadDefectList();
}

function renderModuleBarChart() {
    const ctx = document.getElementById("module-bar-chart");
    if (!ctx || !sysfuncData) return;

    if (moduleBarChart) moduleBarChart.destroy();

    let sysfuncs = (sysfuncData.sysfuncs || []).filter(s => s.open_count > 0);
    sysfuncs.sort((a, b) => b.open_count - a.open_count);
    sysfuncs = sysfuncs.slice(0, 12);

    const labels = sysfuncs.map(s => s.acronym);
    const data = sysfuncs.map(s => s.open_count);

    moduleBarChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: "#f97316",
                borderRadius: { topLeft: 4, topRight: 4 },
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: { top: 20 }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#1a1a1a",
                    titleColor: "#fff",
                    bodyColor: "#ccc",
                    borderColor: "#333",
                    borderWidth: 1,
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        color: "#94a3b8",
                        font: { size: 10 },
                        maxRotation: 30,
                        minRotation: 30,
                    },
                },
                y: {
                    grid: { color: "rgba(255,255,255,0.05)" },
                    ticks: { color: "#94a3b8", font: { size: 11 } },
                    beginAtZero: true,
                }
            }
        },
        plugins: [{
            id: "barLabels",
            afterDatasetsDraw(chart) {
                const { ctx: c } = chart;
                chart.getDatasetMeta(0).data.forEach((bar, i) => {
                    const value = data[i];
                    c.save();
                    c.font = "bold 11px Segoe UI";
                    c.fillStyle = "#ccc";
                    c.textAlign = "center";
                    c.fillText(value, bar.x, bar.y - 6);
                    c.restore();
                });
            }
        }]
    });
}

// --- Load Defect List ---
function getCategorySysfuncs(category) {
    if (!sysfuncData || !category) return "";
    return (sysfuncData.sysfuncs || [])
        .filter(s => s.category === category)
        .map(s => s.acronym)
        .join(",");
}

async function loadDefectList() {
    const extra = { page: currentPage, status: "open" };
    if (selectedSysfunc) {
        extra.sysfunc = selectedSysfunc;
    } else if (selectedCategory) {
        const catSysfuncs = getCategorySysfuncs(selectedCategory);
        if (catSysfuncs) extra.sysfunc = catSysfuncs;
    }

    try {
        const res = await fetch(`/api/jira/list${buildQueryString(extra)}`);
        if (!res.ok) throw new Error(await res.text());
        defectListData = await res.json();
        renderDefectList();
    } catch (e) {
        console.error("Defect list error:", e);
    }
}

function renderDefectList() {
    const tbody = document.getElementById("defect-list-body");
    const title = document.getElementById("defect-list-title");
    const countEl = document.getElementById("defect-count");
    if (!tbody || !defectListData) return;

    title.textContent = selectedSysfunc ? `Defect List — ${selectedSysfunc}` : "Defect List";
    countEl.textContent = `${defectListData.total} defects`;

    const issues = defectListData.issues || [];
    if (issues.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="no-data">No defects found</td></tr>`;
        renderPagination();
        return;
    }

    tbody.innerHTML = issues.map(i => `
        <tr>
            <td class="key-cell">
                <a href="${JIRA_BASE}/browse/${i.key}" target="_blank" rel="noopener">${escapeHtml(i.key)}</a>
            </td>
            <td><span class="status-pill" style="background:${i.status_color}20;color:${i.status_color};border:1px solid ${i.status_color}40">${escapeHtml(i.status)}</span></td>
            <td><span class="priority-dot" style="background:${i.priority_color}"></span> ${escapeHtml(i.priority)}</td>
            <td class="summary-cell" title="${escapeHtml(i.summary)}">${escapeHtml(i.summary)}</td>
            <td class="person-cell">${escapeHtml(i.reporter)}</td>
            <td class="person-cell">${escapeHtml(i.assignee)}</td>
            <td class="comment-cell" title="${i.latest_comment ? escapeHtml(i.latest_comment.body) : ''}">${i.latest_comment ? escapeHtml(i.latest_comment.body) : '<span style="color:var(--text-muted)">—</span>'}</td>
        </tr>
    `).join("");

    renderPagination();
}

function renderPagination() {
    const container = document.getElementById("pagination");
    if (!container || !defectListData) return;

    const { page, total_pages } = defectListData;
    if (total_pages <= 1) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = `
        <button class="btn btn-secondary btn-sm" ${page <= 1 ? "disabled" : ""} onclick="goToPage(${page - 1})">Prev</button>
        <span class="page-info">Page ${page} of ${total_pages}</span>
        <button class="btn btn-secondary btn-sm" ${page >= total_pages ? "disabled" : ""} onclick="goToPage(${page + 1})">Next</button>
    `;
}

function goToPage(p) {
    currentPage = p;
    loadDefectList();
}

// --- Controls ---
function applyFilters() {
    selectedCategory = null;
    selectedSysfunc = null;
    currentPage = 1;
    loadAll();
}

function resetFilters() {
    document.getElementById("filter-release").value = "";
    document.getElementById("filter-candidate").value = "";
    document.getElementById("filter-safety").value = "";
    selectedCategory = null;
    selectedSysfunc = null;
    currentPage = 1;
    loadAll();
}

async function refreshData() {
    await fetch("/api/jira/cache-clear");
    loadAll();
}

async function loadAll() {
    showError(false);
    const isFirstLoad = !overviewData;
    if (isFirstLoad) showLoading(true);
    try {
        await Promise.all([loadOverview(), loadSysfunc(), loadDefectList()]);
        _lastFetchTime = Date.now();
        showOfflineBanner(false);
    } catch (e) {
        showOfflineBanner(true);
        if (isFirstLoad) showError(true, e.message);
    } finally {
        if (isFirstLoad) showLoading(false);
    }
}

// --- Offline Banner ---
function showOfflineBanner(show) {
    let banner = document.getElementById("defect-offline-banner");
    if (show && !banner) {
        banner = document.createElement("div");
        banner.id = "defect-offline-banner";
        banner.style.cssText = "position:fixed;top:60px;left:50%;transform:translateX(-50%);background:var(--accent-red);color:#fff;padding:0.5rem 1.5rem;border-radius:4px;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;z-index:500;animation:fadeInUp 0.3s ease;";
        banner.textContent = "Jira API Offline — Reconnecting...";
        document.body.appendChild(banner);
    } else if (!show && banner) {
        banner.remove();
    }
}

// --- Updated Timer ---
function updateLastUpdated() {
    const el = document.getElementById("defect-last-updated");
    if (!el) return;
    const secs = Math.floor((Date.now() - _lastFetchTime) / 1000);
    if (secs < 3) el.textContent = "Updated: just now";
    else if (secs < 60) el.textContent = `Updated: ${secs}s ago`;
    else el.textContent = `Updated: ${Math.floor(secs / 60)}m ago`;
}

// --- Page Visibility API ---
document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        _lastActiveTime = Date.now();
    } else {
        const hiddenDuration = Date.now() - _lastActiveTime;
        if (hiddenDuration > 10 * 60 * 1000) {
            window.location.reload();
        } else {
            loadAll();
        }
    }
});

// --- Init ---
document.addEventListener("DOMContentLoaded", () => {
    loadAll();
    setInterval(loadAll, AUTO_REFRESH_INTERVAL);
    setInterval(updateLastUpdated, 1000);
});
