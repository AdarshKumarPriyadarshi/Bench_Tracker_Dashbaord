const REFRESH_INTERVAL = 10000;
let benchData = [];
let prevStatusMap = {};
let prevDetailMap = {};
let isFirstLoad = true;

const BENCH_ALIASES = {1: "Vijayanagara", 2: "Maurya", 3: "Chola", 4: "Magadha", 5: "Pallava"};

function showToast(type, title, sub) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-dot"></span><div class="toast-body"><span class="toast-title">${title}</span><span class="toast-sub">${sub}</span></div>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("toast-out");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function buildDetailMap(data) {
    const map = {};
    data.forEach(b => {
        map[`${b.bench_id}_${b.pc_type}`] = {
            status: b.status,
            short_id: b.short_id || "",
            user_name: b.user_name || "",
            bench_id: b.bench_id,
            pc_type: b.pc_type,
        };
    });
    return map;
}

function detectAndNotify(oldMap, newMap) {
    if (isFirstLoad) return;
    for (const key in newMap) {
        const oldEntry = oldMap[key];
        const newEntry = newMap[key];
        if (!oldEntry) continue;
        const bench = BENCH_ALIASES[newEntry.bench_id] || `Bench ${newEntry.bench_id}`;
        const pc = newEntry.pc_type === "windows" ? "Windows" : "Linux";

        if (oldEntry.status !== "occupied" && newEntry.status === "occupied") {
            const name = newEntry.user_name ? `${newEntry.short_id} (${newEntry.user_name})` : newEntry.short_id;
            showToast("checkin", `${name} checked in`, `${bench} \u2022 ${pc}`);
        } else if (oldEntry.status === "occupied" && newEntry.status !== "occupied") {
            const name = oldEntry.user_name ? `${oldEntry.short_id} (${oldEntry.user_name})` : oldEntry.short_id;
            showToast("checkout", `${name} checked out`, `${bench} \u2022 ${pc}`);
        }
    }
}

const ICONS = {
    windows: `<svg class="pc-icon-svg" viewBox="0 0 24 24" fill="currentColor"><path d="M3 12V6.75l6-0.75v6H3zm7-0.9V5.55l8-1.05v7.5h-8V11.1zM11 13h8v7.5l-8-1.05V13zm-8 0h6v5.75l-6-0.75V13z"/></svg>`,
    linux: `<svg class="pc-icon-svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 2c1.86 0 3.55.68 4.88 1.78L5.78 16.88A7.96 7.96 0 014 12c0-4.42 3.58-8 8-8zm0 16c-1.86 0-3.55-.68-4.88-1.78L18.22 7.12A7.96 7.96 0 0120 12c0 4.42-3.58 8-8 8z"/></svg>`,
    clock: `<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
    wifi: `<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>`,
    monitor: `<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
    chat: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>`,
};

function buildStatusMap(data) {
    const map = {};
    data.forEach(b => {
        map[`${b.bench_id}_${b.pc_type}`] = b.status;
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

async function fetchBenches() {
    try {
        const res = await fetch("/api/benches");
        const newData = await res.json();
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
        console.error("Failed to fetch bench data:", err);
    }
}

function formatDuration(isoString) {
    if (!isoString) return "\u2014";
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

function getTeamsLink(email, benchName, benchAlias) {
    if (!email) return "#";
    const bench = benchAlias || benchName;
    return `https://teams.microsoft.com/l/chat/0/0?users=${email}&message=Hi! I need ${bench} bench. Please ping me when you're done.`;
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    if (!text) return "";
    return text.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function renderSlotContent(data, benchName, benchAlias) {
    if (!data) return `<div class="empty-state"><span class="empty-icon">\u2014</span><span class="empty-text">No data</span></div>`;

    const isOccupied = data.status === "occupied";
    const pcLabel = data.pc_type === "windows" ? "Windows" : "Linux";
    const icon = data.pc_type === "windows" ? ICONS.windows : ICONS.linux;
    const hostname = data.pc_type === "windows" ? (data.win_hostname || "") : (data.lin_hostname || "");

    if (!isOccupied) {
        return `
            <div class="pc-slot-inner">
                <div class="pc-label">${icon} ${pcLabel}</div>
                <span class="status-badge status-available">
                    <span class="status-dot"></span> Available
                </span>
                ${hostname ? `<div class="user-meta"><div class="meta-row">${ICONS.monitor} <span class="hostname-text">${escapeHtml(hostname)}</span></div></div>` : ""}
                <div class="empty-state">
                    <span class="empty-text">Ready to use</span>
                </div>
            </div>`;
    }

    const accessLabel = {rdp: "RDP", nomachine: "NoMachine", physical: "Physical"}[data.access_method] || data.access_method || "\u2014";
    const durationMins = getDurationMinutes(data.start_time);
    const timerClass = durationMins > 120 ? "timer timer-long" : "timer";

    return `
        <div class="pc-slot-inner">
            <div class="pc-label">${icon} ${pcLabel}</div>
            <span class="status-badge status-occupied">
                <span class="status-dot"></span> Occupied
            </span>
            <div class="user-info">
                <div class="user-id">${escapeHtml(data.short_id)}${data.user_name ? ` <span style="font-weight:300;font-size:0.8rem;color:var(--text-secondary)">— ${escapeHtml(data.user_name)}</span>` : ""}</div>
                <div class="user-purpose">${escapeHtml(data.purpose)}</div>
                <div class="user-meta">
                    ${hostname ? `<div class="meta-row">${ICONS.monitor} <span class="hostname-text">${escapeHtml(hostname)}</span></div>` : ""}
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
                    <a href="${getTeamsLink(data.user_email, benchName || '', benchAlias || '')}" target="_blank" class="btn btn-teams">${ICONS.chat} Teams</a>
                </div>
            </div>
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
            const benchName = win?.bench_name || lin?.bench_name || `Bench ${id}`;
            const benchAlias = win?.bench_alias || lin?.bench_alias || "";
            const aliasHtml = benchAlias ? `<span class="bench-alias">${escapeHtml(benchAlias)}</span>` : "";
            const anyOccupied = win?.status === "occupied" || lin?.status === "occupied";
            const cardClass = anyOccupied ? "has-occupied" : "all-available";

            html += `
                <div class="bench-card initial-load ${cardClass}" data-bench-id="${id}">
                    <div class="bench-header" onclick="window.location='/bench/${id}'" style="cursor:pointer">
                        <div class="bench-header-left">
                            <span class="bench-name">${escapeHtml(benchName)}</span>
                            ${aliasHtml}
                        </div>
                        <div class="bench-status-indicator">
                            <span class="bench-ecu"><span class="ecu-dot"></span> ECU</span>
                        </div>
                    </div>
                    <div class="pc-slots">
                        <div class="pc-slot ${win?.status === 'occupied' ? 'occupied' : 'available'}" data-slot="${id}_windows">
                            ${renderSlotContent(win, benchName, benchAlias)}
                        </div>
                        <div class="pc-slot ${lin?.status === 'occupied' ? 'occupied' : 'available'}" data-slot="${id}_linux">
                            ${renderSlotContent(lin, benchName, benchAlias)}
                        </div>
                    </div>
                </div>`;
        }
        grid.innerHTML = html;
        return;
    }

    for (let id = 1; id <= 5; id++) {
        const win = grouped[id]?.windows;
        const lin = grouped[id]?.linux;
        const benchName = win?.bench_name || lin?.bench_name || `Bench ${id}`;
        const benchAlias = win?.bench_alias || lin?.bench_alias || "";
        const anyOccupied = win?.status === "occupied" || lin?.status === "occupied";
        const card = grid.querySelector(`[data-bench-id="${id}"]`);
        if (!card) continue;

        card.classList.remove("has-occupied", "all-available", "card-changed");
        card.classList.add(anyOccupied ? "has-occupied" : "all-available");

        const winSlot = card.querySelector(`[data-slot="${id}_windows"]`);
        const linSlot = card.querySelector(`[data-slot="${id}_linux"]`);

        if (changedSlots.has(`${id}_windows`) && winSlot) {
            winSlot.className = `pc-slot ${win?.status === 'occupied' ? 'occupied' : 'available'} status-changed`;
            winSlot.innerHTML = renderSlotContent(win, benchName, benchAlias);
            card.classList.add("card-changed");
        }

        if (changedSlots.has(`${id}_linux`) && linSlot) {
            linSlot.className = `pc-slot ${lin?.status === 'occupied' ? 'occupied' : 'available'} status-changed`;
            linSlot.innerHTML = renderSlotContent(lin, benchName, benchAlias);
            card.classList.add("card-changed");
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
    const total = benchData.length;
    const occupied = benchData.filter(b => b.status === "occupied").length;
    const available = total - occupied;
    const uniqueUsers = new Set(benchData.filter(b => b.short_id).map(b => b.short_id)).size;

    const el = id => document.getElementById(id);
    animateValue(el("stat-available"), available);
    animateValue(el("stat-occupied"), occupied);
    animateValue(el("stat-users"), uniqueUsers);
    animateValue(el("stat-total"), total);
}

function updateTimers() {
    document.querySelectorAll(".timer[data-start]").forEach(el => {
        el.textContent = formatDuration(el.dataset.start);
        const mins = getDurationMinutes(el.dataset.start);
        if (mins > 120) {
            el.classList.add("timer-long");
        } else {
            el.classList.remove("timer-long");
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    fetchBenches();
    setInterval(fetchBenches, REFRESH_INTERVAL);
    setInterval(updateTimers, 1000);
});


/* ═══════════ HISTORY PAGE ═══════════ */

async function fetchHistory() {
    const benchFilter = document.getElementById("filter-bench")?.value || "";
    const userFilter = document.getElementById("filter-user")?.value?.trim() || "";

    let url = "/api/history?limit=200";
    if (benchFilter) url += `&bench_id=${benchFilter}`;
    if (userFilter) url += `&short_id=${encodeURIComponent(userFilter)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        renderHistory(data);
    } catch (err) {
        console.error("Failed to fetch history:", err);
    }
}

function renderHistory(records) {
    const tbody = document.getElementById("history-body");
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="no-data">No usage history found</td></tr>`;
        return;
    }

    tbody.innerHTML = records.map(r => `
        <tr>
            <td>Bench ${r.bench_id}</td>
            <td style="text-transform:capitalize">${r.pc_type}</td>
            <td><strong style="color:var(--text-primary);letter-spacing:0.04em">${escapeHtml(r.short_id)}</strong></td>
            <td>${escapeHtml(r.purpose)}</td>
            <td><span class="access-badge">${r.access_method || "\u2014"}</span></td>
            <td>${formatDateTime(r.start_time)}</td>
            <td>${formatDateTime(r.end_time)}</td>
            <td style="font-variant-numeric:tabular-nums">${r.duration_min ? r.duration_min.toFixed(1) + " min" : "\u2014"}</td>
        </tr>
    `).join("");
}

function formatDateTime(iso) {
    if (!iso) return "\u2014";
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: true,
    });
}
