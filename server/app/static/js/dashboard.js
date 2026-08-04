const REFRESH_INTERVAL = 5000;
let benchData = [];
let prevStatusMap = {};
let prevDetailMap = {};
let isFirstLoad = true;

const BENCH_NAMES = {1: "Vijayanagara", 2: "Maurya", 3: "Chola", 4: "Magadha", 5: "Pallava"};

function showToast(type, title, sub) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-dot"></span><div class="toast-body"><span class="toast-title">${escapeHtml(title)}</span><span class="toast-sub">${escapeHtml(sub)}</span></div>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("toast-out");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function buildDetailMap(data) {
    const map = {};
    data.forEach(b => {
        if (b.pc_type !== "windows") return;
        map[b.bench_id] = {
            status: b.status,
            short_id: b.short_id || "",
            user_name: b.user_name || "",
            bench_id: b.bench_id,
        };
    });
    return map;
}

function requestNotificationPermission() {
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }
}

function sendBrowserNotification(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, {
            body: body,
            icon: "/static/MBRDI.png",
            silent: false,
        });
    }
}

function detectAndNotify(oldMap, newMap) {
    if (isFirstLoad) return;
    for (const key in newMap) {
        const oldEntry = oldMap[key];
        const newEntry = newMap[key];
        if (!oldEntry) continue;
        const bench = BENCH_NAMES[newEntry.bench_id] || `Bench ${newEntry.bench_id}`;

        if (oldEntry.status !== "occupied" && newEntry.status === "occupied") {
            const name = newEntry.user_name ? `${newEntry.short_id} (${newEntry.user_name})` : newEntry.short_id;
            showToast("checkin", `${name} checked in`, bench);
            sendBrowserNotification(`${bench} — Occupied`, `${name} checked in`);
        } else if (oldEntry.status === "occupied" && newEntry.status !== "occupied") {
            const name = oldEntry.user_name ? `${oldEntry.short_id} (${oldEntry.user_name})` : oldEntry.short_id;
            showToast("checkout", `${name} checked out`, bench);
            sendBrowserNotification(`${bench} — Available`, `${name} checked out`);
        }
    }
}

const ICONS = {
    windows: `<svg class="pc-icon-svg" viewBox="0 0 24 24" fill="currentColor"><path d="M3 12V6.75l6-0.75v6H3zm7-0.9V5.55l8-1.05v7.5h-8V11.1zM11 13h8v7.5l-8-1.05V13zm-8 0h6v5.75l-6-0.75V13z"/></svg>`,
    linux: `<svg class="pc-icon-svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="16"><circle cx="128" cy="128" r="118"/><circle cx="128" cy="128" r="54"/><circle cx="69" cy="128" r="14" fill="currentColor"/><circle cx="159" cy="73" r="14" fill="currentColor"/><circle cx="159" cy="183" r="14" fill="currentColor"/></svg>`,
    clock: `<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
    wifi: `<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>`,
    chat: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>`,
};

function buildStatusMap(data) {
    const map = {};
    data.forEach(b => {
        map[`${b.bench_id}_${b.pc_type}`] = `${b.status}_${b.short_id || ''}_${b.purpose || ''}`;
    });
    return map;
}

function getChangedSlots(oldMap, newMap) {
    const changed = new Set();
    for (const key in newMap) {
        if (oldMap[key] !== newMap[key]) changed.add(key);
    }
    return changed;
}

function showOfflineBanner(show) {
    let banner = document.getElementById("offline-banner");
    if (show && !banner) {
        banner = document.createElement("div");
        banner.id = "offline-banner";
        banner.style.cssText = "position:fixed;top:60px;left:50%;transform:translateX(-50%);background:var(--accent-red);color:#fff;padding:0.5rem 1.5rem;border-radius:4px;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;z-index:500;animation:fadeInUp 0.3s ease;";
        banner.textContent = "Server Offline — Reconnecting...";
        document.body.appendChild(banner);
    } else if (!show && banner) {
        banner.remove();
    }
}

async function fetchBenches() {
    try {
        const res = await fetch("/api/benches");
        const newData = await res.json();
        showOfflineBanner(false);
        _lastFetchTime = Date.now();
        const newStatusMap = buildStatusMap(newData);
        const newDetailMap = buildDetailMap(newData);
        const changedSlots = getChangedSlots(prevStatusMap, newStatusMap);
        detectAndNotify(prevDetailMap, newDetailMap);
        benchData = newData;
        renderDashboard(changedSlots);
        updateStats();
        prevStatusMap = newStatusMap;
        prevDetailMap = newDetailMap;
        isFirstLoad = false;
    } catch (err) {
        showOfflineBanner(true);
        console.error("Failed to fetch bench data:", err);
    }
}

function formatDuration(isoString) {
    if (!isoString) return "—";
    const start = new Date(isoString);
    const now = new Date();
    const diffMs = now - start;
    const secs = Math.floor(diffMs / 1000);
    const mins = Math.floor(secs / 60);
    const hrs = Math.floor(mins / 60);
    const remainMins = mins % 60;
    const remainSecs = secs % 60;
    if (hrs > 0) return `${hrs}h ${String(remainMins).padStart(2, '0')}m ${String(remainSecs).padStart(2, '0')}s`;
    if (mins > 0) return `${mins}m ${String(remainSecs).padStart(2, '0')}s`;
    return `${secs}s`;
}

function getDurationMinutes(isoString) {
    if (!isoString) return 0;
    return Math.floor((new Date() - new Date(isoString)) / 60000);
}


function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function renderBenchCard(win, lin) {
    const benchId = win?.bench_id || lin?.bench_id;
    const benchName = win?.bench_name || lin?.bench_name || BENCH_NAMES[benchId] || `Bench ${benchId}`;
    const architecture = win?.architecture || lin?.architecture || "";
    const swVersion = win?.sw_version || lin?.sw_version || "";
    const winHostname = win?.win_hostname || "";
    const linHostname = win?.lin_hostname || lin?.lin_hostname || "";
    const isOccupied = win?.status === "occupied";
    const data = win || lin;
    const isFlashing = isOccupied && data.purpose && data.purpose.toLowerCase().includes("flashing");
    const cardClass = isFlashing ? "has-flashing" : (isOccupied ? "has-occupied" : "all-available");

    let bodyHtml = "";
    if (!isOccupied) {
        bodyHtml = `
            <div class="bench-card-body">
                <span class="status-badge status-available">
                    <span class="status-dot"></span> Available
                </span>
                <div class="hostnames-row">
                    <div class="hostname-col">
                        <div class="hostname-label">${ICONS.windows} Windows</div>
                        <span class="hostname-text">${escapeHtml(winHostname)}</span>
                    </div>
                    <div class="hostname-col">
                        <div class="hostname-label">${ICONS.linux} Linux</div>
                        <span class="hostname-text">${escapeHtml(linHostname)}</span>
                    </div>
                </div>
                <div class="pc-actions">
                    <button class="btn btn-restart" onclick="confirmRestart('${benchId}', '${escapeHtml(benchName)}')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg> Restart</button>
                </div>
                <div class="empty-state">
                    <span class="empty-text">Ready to use</span>
                </div>
            </div>`;
    } else {
        const accessLabel = {rdp: "RDP", nomachine: "NoMachine", physical: "Physical"}[data.access_method] || data.access_method || "—";
        const durationMins = getDurationMinutes(data.start_time);
        const timerClass = durationMins > 120 ? "timer timer-long" : "timer";

        bodyHtml = `
            <div class="bench-card-body">
                <span class="status-badge status-occupied">
                    <span class="status-dot"></span> Occupied
                </span>
                <div class="hostnames-row">
                    <div class="hostname-col">
                        <div class="hostname-label">${ICONS.windows} Windows</div>
                        <span class="hostname-text">${escapeHtml(winHostname)}</span>
                    </div>
                    <div class="hostname-col">
                        <div class="hostname-label">${ICONS.linux} Linux</div>
                        <span class="hostname-text">${escapeHtml(linHostname)}</span>
                    </div>
                </div>
                <div class="user-info">
                    <div class="user-id">${escapeHtml(data.short_id)}${data.user_name ? ` <span style="font-weight:300;font-size:0.8rem;color:var(--text-secondary)">— ${escapeHtml(data.user_name)}</span>` : ""}</div>
                    <div class="user-purpose">${escapeHtml(data.purpose)}</div>
                    <div class="user-meta">
                        <div class="meta-row">
                            ${ICONS.clock}
                            <span class="${timerClass}" data-start="${data.start_time}">${formatDuration(data.start_time)}</span>
                        </div>
                        <div class="meta-row">
                            ${ICONS.wifi}
                            <span class="access-badge">${accessLabel}</span>
                        </div>
                    </div>
                    <div class="pc-actions">
                        <button class="btn btn-release" onclick="openReleaseModal('${benchId}', '${escapeHtml(benchName)}')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg> Request</button>
                        ${data.access_method === "physical" ? `<button class="btn btn-manual-release" onclick="manualRelease(${benchId})"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg> Release</button>` : ""}
                    </div>
                </div>
            </div>`;
    }

    return `
        <div class="bench-card initial-load ${cardClass}" data-bench-id="${benchId}">
            <div class="bench-header" onclick="window.location='/bench/${benchId}'" style="cursor:pointer">
                <div class="bench-header-left">
                    <span class="bench-name">${escapeHtml(benchName)}</span>
                    ${swVersion ? `<span class="bench-sw-version">SW : ${escapeHtml(swVersion)}</span>` : ""}
                </div>
                <div class="bench-status-indicator">
                    ${architecture ? `<span class="bench-ecu"><span class="ecu-dot"></span> ${escapeHtml(architecture)}</span>` : ""}
                </div>
            </div>
            ${bodyHtml}
        </div>`;
}

function renderDashboard(changedSlots = new Set()) {
    const grid = document.getElementById("bench-grid");
    if (!grid) return;

    const grouped = {};
    benchData.forEach(b => {
        if (!grouped[b.bench_id]) grouped[b.bench_id] = {};
        grouped[b.bench_id][b.pc_type] = b;
    });

    const isInitial = grid.children.length === 0;

    if (isInitial) {
        let html = "";
        for (let id = 1; id <= 5; id++) {
            const win = grouped[id]?.windows;
            const lin = grouped[id]?.linux;
            html += renderBenchCard(win, lin);
        }
        grid.innerHTML = html;
        return;
    }

    for (let id = 1; id <= 5; id++) {
        const hasChange = changedSlots.has(`${id}_windows`) || changedSlots.has(`${id}_linux`);
        if (!hasChange) continue;

        const win = grouped[id]?.windows;
        const lin = grouped[id]?.linux;
        const existingCard = grid.querySelector(`[data-bench-id="${id}"]`);
        if (existingCard) {
            const temp = document.createElement("div");
            temp.innerHTML = renderBenchCard(win, lin);
            const newCard = temp.firstElementChild;
            newCard.classList.remove("initial-load");
            newCard.classList.add("card-changed");
            existingCard.replaceWith(newCard);
        }
    }
}

function animateValue(el, newVal) {
    if (!el) return;
    const oldVal = parseInt(el.textContent) || 0;
    if (oldVal === newVal) return;

    const duration = 500;
    const steps = 15;
    const stepTime = duration / steps;
    const diff = newVal - oldVal;
    let step = 0;

    el.classList.add("counting");

    const interval = setInterval(() => {
        step++;
        const progress = step / steps;
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(oldVal + diff * eased);
        if (step >= steps) {
            clearInterval(interval);
            el.textContent = newVal;
            setTimeout(() => el.classList.remove("counting"), 100);
        }
    }, stepTime);
}

function updateStats() {
    const benchIds = new Set(benchData.map(b => b.bench_id));
    const total = benchIds.size;
    const occupiedBenches = new Set(benchData.filter(b => b.status === "occupied").map(b => b.bench_id)).size;
    const available = total - occupiedBenches;
    const uniqueUsers = new Set(benchData.filter(b => b.short_id).map(b => b.short_id)).size;

    const el = id => document.getElementById(id);
    animateValue(el("stat-available"), available);
    animateValue(el("stat-occupied"), occupiedBenches);
    animateValue(el("stat-users"), uniqueUsers);
    animateValue(el("stat-total"), total);
}

function updateTimers() {
    document.querySelectorAll(".timer[data-start]").forEach(el => {
        el.textContent = formatDuration(el.dataset.start);
        const mins = getDurationMinutes(el.dataset.start);
        if (mins > 60) {
            el.style.color = "#ff1744";
        } else if (mins > 45) {
            el.style.color = "#ff6e40";
        } else if (mins > 30) {
            el.style.color = "#ffa726";
        } else if (mins > 15) {
            el.style.color = "#ffd740";
        } else {
            el.style.color = "#ffffff";
        }
    });
}

let _lastFetchTime = Date.now();

function updateLastUpdated() {
    const el = document.getElementById("last-updated");
    if (!el) return;
    const secs = Math.floor((Date.now() - _lastFetchTime) / 1000);
    if (secs < 3) el.textContent = "Updated: just now";
    else el.textContent = `Updated: ${secs}s ago`;
}

document.addEventListener("DOMContentLoaded", () => {
    requestNotificationPermission();
    fetchBenches();
    setInterval(fetchBenches, REFRESH_INTERVAL);
    setInterval(updateTimers, 1000);
    setInterval(updateLastUpdated, 1000);
});

let _lastActiveTime = Date.now();

document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        _lastActiveTime = Date.now();
    } else {
        const hiddenDuration = Date.now() - _lastActiveTime;
        if (hiddenDuration > 10 * 60 * 1000) {
            window.location.reload();
        } else {
            fetchBenches();
        }
    }
});


/* ═══════════ HISTORY PAGE ═══════════ */

let userMap = {};

async function loadUserMap() {
    try {
        const res = await fetch("/api/users");
        const users = await res.json();
        users.forEach(u => { userMap[u.short_id] = u.name; });
    } catch (e) {}
}

async function fetchHistory() {
    if (Object.keys(userMap).length === 0) await loadUserMap();

    const benchFilter = document.getElementById("filter-bench")?.value || "";
    const userFilter = document.getElementById("filter-user")?.value?.trim().toUpperCase() || "";

    const limitFilter = document.getElementById("filter-limit")?.value || "200";
    let url = `/api/history?limit=${limitFilter}`;
    if (benchFilter) url += `&bench_id=${benchFilter}`;

    try {
        const res = await fetch(url);
        let data = await res.json();
        if (userFilter) {
            data = data.filter(r => r.short_id && r.short_id.toUpperCase().startsWith(userFilter));
        }
        renderHistory(data);
    } catch (err) {
        console.error("Failed to fetch history:", err);
    }
}

function renderHistory(records) {
    const tbody = document.getElementById("history-body");
    if (!tbody) return;

    lastHistoryData = records;

    const seen = new Set();
    const filtered = records.filter(r => {
        const key = `${r.bench_id}_${r.start_time}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="no-data">No usage history found</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(r => `
        <tr>
            <td>${BENCH_NAMES[r.bench_id] || 'Bench ' + r.bench_id}</td>
            <td style="color:var(--text-primary);letter-spacing:0.04em">${escapeHtml(r.short_id)}${userMap[r.short_id] ? ` <span style="color:var(--text-muted);font-size:0.75rem;">— ${escapeHtml(userMap[r.short_id])}</span>` : ""}</td>
            <td>${escapeHtml(r.purpose)}</td>
            <td>${formatDateTime(r.start_time)}</td>
            <td>${formatDateTime(r.end_time)}</td>
            <td style="font-variant-numeric:tabular-nums">${r.duration_min ? r.duration_min.toFixed(1) + " min" : "—"}</td>
        </tr>
    `).join("");
}

let lastHistoryData = [];

function exportCSV() {
    if (lastHistoryData.length === 0) return;
    const headers = ["Bench", "User", "Name", "Purpose", "Start Time", "End Time", "Duration (min)"];
    const rows = lastHistoryData.map(r => [
        BENCH_NAMES[r.bench_id] || `Bench ${r.bench_id}`,
        r.short_id,
        userMap[r.short_id] || "",
        r.purpose,
        r.start_time || "",
        r.end_time || "",
        r.duration_min ? r.duration_min.toFixed(1) : ""
    ]);
    const csv = [headers, ...rows].map(row => row.map(c => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bench_usage_history.csv";
    a.click();
    URL.revokeObjectURL(url);
}

function getDurationColor(mins) {
    if (!mins) return "var(--text-secondary)";
    if (mins > 60) return "#ff1744";
    if (mins > 45) return "#ff6e40";
    if (mins > 30) return "#ffa726";
    if (mins > 15) return "#ffd740";
    return "#ffffff";
}

function formatDateTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: true,
    });
}


/* ═══════════ RESTART CONFIRMATION ═══════════ */

function confirmRestart(benchId, benchName) {
    let modal = document.getElementById("restart-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "restart-modal";
        modal.innerHTML = `
            <div class="release-overlay" onclick="closeRestartModal()"></div>
            <div class="release-dialog">
                <h3>CONFIRM RESTART</h3>
                <p style="color:var(--text-secondary);font-size:0.85rem;text-align:center;margin-bottom:1rem;">
                    Are you sure you want to restart <strong id="restart-bench-name" style="color:var(--accent-red)"></strong>?
                </p>
                <p style="color:var(--accent-amber);font-size:0.75rem;text-align:center;margin-bottom:1.5rem;">
                    &#9888; Any unsaved data on the bench will be lost.
                </p>
                <div class="release-error" id="restart-error"></div>
                <div style="display:flex;gap:0.8rem;">
                    <button class="btn btn-secondary" onclick="closeRestartModal()" style="flex:1;padding:0.7rem;">CANCEL</button>
                    <button class="btn btn-restart-win" onclick="sendRestart('windows')" style="flex:1;padding:0.7rem;">WINDOWS</button>
                    <button class="btn btn-restart-lin" onclick="sendRestart('linux')" style="flex:1;padding:0.7rem;">LINUX</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    document.getElementById("restart-bench-name").textContent = benchName;
    document.getElementById("restart-error").textContent = "";
    document.getElementById("restart-error").style.color = "";
    modal.querySelector(".btn-restart-win").disabled = false;
    modal.querySelector(".btn-restart-lin").disabled = false;
    modal.dataset.benchId = benchId;
    modal.style.display = "flex";
}

function closeRestartModal() {
    const modal = document.getElementById("restart-modal");
    if (modal) modal.style.display = "none";
}

async function sendRestart(pcType) {
    const modal = document.getElementById("restart-modal");
    const benchId = modal.dataset.benchId;
    const errorEl = document.getElementById("restart-error");
    const winBtn = modal.querySelector(".btn-restart-win");
    const linBtn = modal.querySelector(".btn-restart-lin");

    winBtn.disabled = true;
    linBtn.disabled = true;
    errorEl.style.color = "var(--accent-amber)";
    errorEl.textContent = `Restarting ${pcType}...`;

    try {
        const res = await fetch("/api/restart-bench", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ bench_id: parseInt(benchId), pc_type: pcType })
        });
        closeRestartModal();
        if (res.ok) {
            showToast("checkout", "Restart signal sent", `${pcType.charAt(0).toUpperCase() + pcType.slice(1)}`);
        } else {
            const data = await res.json();
            showToast("checkin", "Restart failed", data.detail || "Error");
        }
    } catch (e) {
        closeRestartModal();
        showToast("checkin", "Restart failed", "Server error");
    }
}


/* ═══════════ RELEASE REQUEST MODAL ═══════════ */

let releaseUsers = [];

async function loadReleaseUsers() {
    try {
        const res = await fetch("/api/benches");
        const data = await res.json();
        const users = new Set();
        data.forEach(b => { if (b.short_id) users.add(b.short_id); });
        releaseUsers = [...users].sort();
    } catch (e) {}
}

async function manualRelease(benchId) {
    if (!confirm("Are you sure you want to release this bench?")) return;
    try {
        const res = await fetch("/api/checkout", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ bench_id: benchId, pc_type: "windows" })
        });
        if (res.ok) {
            showToast("checkout", "Bench released manually", BENCH_NAMES[benchId] || `Bench ${benchId}`);
            fetchBenches();
        } else {
            showToast("checkin", "Release failed", "Bench may already be available");
        }
    } catch (e) {
        showToast("checkin", "Release failed", "Server error");
    }
}

function openReleaseModal(benchId, benchName) {
    let modal = document.getElementById("release-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "release-modal";
        modal.innerHTML = `
            <div class="release-overlay" onclick="closeReleaseModal()"></div>
            <div class="release-dialog">
                <h3>REQUEST FOR RELEASE</h3>
                <div class="release-field">
                    <label>BENCH</label>
                    <input type="text" id="release-bench-name" readonly>
                </div>
                <div class="release-field">
                    <label>REQUESTER</label>
                    <select id="release-requester"></select>
                </div>
                <div class="release-field">
                    <label>PURPOSE</label>
                    <select id="release-purpose">
                        <option value="">Select Purpose</option>
                        <option value="Automation Execution">Automation Execution</option>
                        <option value="Automation Integration">Automation Integration</option>
                        <option value="Bench Debugging (HW)">Bench Debugging (HW)</option>
                        <option value="Diagnostic (SEM) Testing">Diagnostic (SEM) Testing</option>
                        <option value="Execution Analysis">Execution Analysis</option>
                        <option value="Log Collection">Log Collection</option>
                        <option value="Manual Execution">Manual Execution</option>
                        <option value="Night Run Execution - DND">Night Run Execution - DND</option>
                        <option value="Software Debugging">Software Debugging</option>
                        <option value="Software Flashing">Software Flashing</option>
                    </select>
                </div>
                <div class="release-error" id="release-error"></div>
                <button class="btn btn-send-release" onclick="sendReleaseRequest()">SEND REQUEST</button>
            </div>
        `;
        document.body.appendChild(modal);
    }

    document.getElementById("release-bench-name").value = benchName;
    modal.dataset.benchId = benchId;
    document.getElementById("release-purpose").value = "";
    document.getElementById("release-error").textContent = "";

    const select = document.getElementById("release-requester");
    fetch("/api/users").then(r => r.json()).then(users => {
        const sorted = users.sort((a, b) => a.short_id.localeCompare(b.short_id));
        select.innerHTML = '<option value="">Select your Short ID</option>' +
            sorted.map(u => `<option value="${u.short_id}">${u.short_id}${u.name ? ' — ' + u.name : ''}</option>`).join("");
    }).catch(() => {
        const allUsers = [...new Set(benchData.map(b => b.short_id).filter(Boolean))].sort();
        select.innerHTML = '<option value="">Select your Short ID</option>' +
            allUsers.map(u => `<option value="${u}">${u}</option>`).join("");
    });

    modal.style.display = "flex";
}

function closeReleaseModal() {
    const modal = document.getElementById("release-modal");
    if (modal) modal.style.display = "none";
}

async function sendReleaseRequest() {
    const modal = document.getElementById("release-modal");
    const benchId = parseInt(modal.dataset.benchId);
    const requester = document.getElementById("release-requester").value;
    const purpose = document.getElementById("release-purpose").value.trim();
    const errorEl = document.getElementById("release-error");

    if (!requester) {
        errorEl.textContent = "Please select your Short ID";
        return;
    }
    if (!purpose) {
        errorEl.textContent = "Please enter a purpose";
        return;
    }

    const bench = benchData.find(b => b.bench_id === benchId && b.pc_type === "windows");
    if (!bench || !bench.user_email) {
        errorEl.textContent = "Cannot find occupant's email";
        return;
    }

    const benchName = bench.bench_name || BENCH_NAMES[benchId] || `Bench ${benchId}`;
    const occupantName = bench.user_name || bench.short_id;
    const message = `Hi ${occupantName}, I need ${benchName} bench for ${purpose}. In how much time will it be free?`;
    const teamsUrl = `https://teams.microsoft.com/l/chat/0/0?users=${encodeURIComponent(bench.user_email)}&message=${encodeURIComponent(message)}`;

    window.open(teamsUrl, "_blank");
    closeReleaseModal();
}
