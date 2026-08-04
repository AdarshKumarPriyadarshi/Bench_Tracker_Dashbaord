const BENCH_NAMES = {1: "Vijayanagara", 2: "Maurya", 3: "Chola", 4: "Magadha", 5: "Pallava"};
const BENCH_COLORS = {
    1: "#2196f3",
    2: "#9c27b0",
    3: "#ff6d00",
    4: "#00bcd4",
    5: "#e91e63",
};

let timelineChart = null;
let dailyChart = null;
let benchChart = null;
let userChart = null;
let allRecords = [];

Chart.defaults.color = "#888888";
Chart.defaults.borderColor = "rgba(255,255,255,0.06)";
Chart.defaults.font.family = "'Segoe UI', sans-serif";

function toLocalDate(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function getDateRange() {
    const fromInput = document.getElementById("filter-from").value;
    const toInput = document.getElementById("filter-to").value;
    if (fromInput && toInput) {
        return { from: fromInput, to: toInput + "T23:59:59" };
    }
    const days = parseInt(document.getElementById("filter-period").value) || 30;
    const to = new Date();
    const from = new Date();
    from.setDate(from.getDate() - days);
    return {
        from: toLocalDate(from),
        to: toLocalDate(to) + "T23:59:59",
    };
}

async function fetchStatistics() {
    const benchId = document.getElementById("filter-bench").value;
    const userId = document.getElementById("filter-user").value;
    const { from, to } = getDateRange();

    let url = `/api/statistics?date_from=${from}&date_to=${to}`;
    if (benchId) url += `&bench_id=${benchId}`;
    if (userId) url += `&short_id=${encodeURIComponent(userId)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        allRecords = data.records || [];

        const noDataEl = document.getElementById("no-data-message");
        if (allRecords.length === 0) {
            if (!noDataEl) {
                const msg = document.createElement("div");
                msg.id = "no-data-message";
                msg.style.cssText = "text-align:center;padding:3rem;color:var(--text-muted);font-size:0.85rem;letter-spacing:0.08em;text-transform:uppercase;";
                msg.textContent = "No usage data found for the selected filters";
                document.querySelector(".charts-grid").before(msg);
            }
            document.querySelector(".charts-grid").style.display = "none";
            document.querySelector(".calendar-panel").style.display = "none";
        } else {
            if (noDataEl) noDataEl.remove();
            document.querySelector(".charts-grid").style.display = "";
            document.querySelector(".calendar-panel").style.display = "";
        }

        renderSummary(data.summary);
        renderTimelineChart(allRecords);
        renderDailyChart(allRecords);
        renderBenchChart(allRecords);
        renderUserChart(allRecords);
        renderCalendar(allRecords);
        populateUserFilter();
    } catch (err) {
        console.error("Failed to fetch statistics:", err);
    }
}

let _allUsersLoaded = false;

async function populateUserFilter() {
    if (_allUsersLoaded) return;
    try {
        const res = await fetch("/api/users");
        const users = await res.json();
        const select = document.getElementById("filter-user");
        const current = select.value;
        const sorted = users.sort((a, b) => a.short_id.localeCompare(b.short_id));
        const options = ['<option value="">All Users</option>'];
        sorted.forEach(u => {
            options.push(`<option value="${u.short_id}" ${u.short_id === current ? 'selected' : ''}>${u.short_id}</option>`);
        });
        select.innerHTML = options.join("");
        _allUsersLoaded = true;
    } catch (e) {}
}

function renderSummary(summary) {
    document.getElementById("sum-sessions").textContent = summary.total_sessions;
    document.getElementById("sum-avg-duration").textContent = formatMinutes(summary.avg_duration_min);
    document.getElementById("sum-total-hours").textContent = (summary.total_duration_min / 60).toFixed(1) + "h";
    document.getElementById("sum-most-used").textContent = BENCH_NAMES[summary.most_used_bench] || "—";
    document.getElementById("sum-top-user").textContent = summary.top_user || "—";
    document.getElementById("sum-busiest-day").textContent = summary.busiest_day ? formatDate(summary.busiest_day) : "—";
}

function formatMinutes(min) {
    if (!min) return "—";
    if (min < 60) return Math.round(min) + "m";
    const h = Math.floor(min / 60);
    const m = Math.round(min % 60);
    return `${h}h ${m}m`;
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function renderTimelineChart(records) {
    const ctx = document.getElementById("timeline-chart").getContext("2d");
    if (timelineChart) timelineChart.destroy();

    const hourCounts = {};
    records.forEach(r => {
        if (!r.start_time) return;
        const hour = new Date(r.start_time).getHours();
        hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    });

    const labels = [];
    const data = [];
    for (let h = 6; h <= 20; h++) {
        labels.push(`${String(h).padStart(2, '0')}:00`);
        data.push(hourCounts[h] || 0);
    }

    timelineChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Sessions Started",
                data,
                backgroundColor: "rgba(64, 196, 255, 0.5)",
                borderColor: "rgba(64, 196, 255, 0.9)",
                borderWidth: 1,
                borderRadius: 3,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => `${ctx.raw} sessions` } }
            },
            scales: {
                x: {
                    title: { display: true, text: "Hour of Day", color: "#888" },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 },
                    title: { display: true, text: "Sessions", color: "#888" },
                    grid: { color: "rgba(255,255,255,0.04)" },
                }
            }
        }
    });
}

function renderDailyChart(records) {
    const ctx = document.getElementById("daily-chart").getContext("2d");
    if (dailyChart) dailyChart.destroy();

    const dayCounts = {};
    records.forEach(r => {
        if (!r.start_time) return;
        const day = r.start_time.slice(0, 10);
        dayCounts[day] = (dayCounts[day] || 0) + 1;
    });

    const sortedDays = Object.keys(dayCounts).sort();
    const labels = sortedDays.map(d => {
        const dt = new Date(d);
        return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
    });
    const data = sortedDays.map(d => dayCounts[d]);

    dailyChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Sessions",
                data,
                backgroundColor: "rgba(64, 196, 255, 0.4)",
                borderColor: "rgba(64, 196, 255, 0.8)",
                borderWidth: 1,
                borderRadius: 3,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => `${ctx.raw} sessions` } }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 },
                    grid: { color: "rgba(255,255,255,0.04)" },
                }
            }
        }
    });
}

function renderBenchChart(records) {
    const ctx = document.getElementById("bench-chart").getContext("2d");
    if (benchChart) benchChart.destroy();

    const benchHours = {};
    records.forEach(r => {
        const bid = r.bench_id;
        benchHours[bid] = (benchHours[bid] || 0) + (r.duration_min || 0) / 60;
    });

    const labels = Object.keys(benchHours).map(id => BENCH_NAMES[id] || `Bench ${id}`);
    const data = Object.values(benchHours).map(v => Math.round(v * 10) / 10);
    const colors = Object.keys(benchHours).map(id => BENCH_COLORS[id] || "#888");

    const totalHours = data.reduce((a, b) => a + b, 0);

    const connectorPlugin = {
        id: 'connectorLabels',
        afterDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(0);
            const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
            const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;

            meta.data.forEach((arc, i) => {
                const midAngle = (arc.startAngle + arc.endAngle) / 2;
                const outerRadius = arc.outerRadius;

                const startX = centerX + Math.cos(midAngle) * outerRadius;
                const startY = centerY + Math.sin(midAngle) * outerRadius;
                const midX = centerX + Math.cos(midAngle) * (outerRadius + 15);
                const midY = centerY + Math.sin(midAngle) * (outerRadius + 15);
                const isLeft = midAngle > Math.PI / 2 && midAngle < 1.5 * Math.PI;
                const endX = isLeft ? midX - 20 : midX + 20;
                const endY = midY;

                ctx.beginPath();
                ctx.moveTo(startX, startY);
                ctx.lineTo(midX, midY);
                ctx.lineTo(endX, endY);
                ctx.strokeStyle = colors[i] || '#888';
                ctx.lineWidth = 1.5;
                ctx.stroke();

                ctx.font = '11px Segoe UI';
                ctx.fillStyle = '#e0e0e0';
                ctx.textAlign = isLeft ? 'right' : 'left';
                ctx.textBaseline = 'middle';
                const textX = isLeft ? endX - 5 : endX + 5;
                ctx.fillText(`${labels[i]}, ${data[i]}h`, textX, endY);
            });
        }
    };

    benchChart = new Chart(ctx, {
        type: "pie",
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: colors.map(c => c + "cc"),
                borderColor: colors,
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: 80 },
            plugins: {
                legend: { position: "right", labels: { boxWidth: 12, padding: 12 } },
                tooltip: {
                    callbacks: { label: ctx => `${ctx.label}: ${ctx.raw}h (${Math.round((ctx.raw / totalHours) * 100)}%)` }
                }
            }
        },
        plugins: [connectorPlugin]
    });
}

function renderUserChart(records) {
    const ctx = document.getElementById("user-chart").getContext("2d");
    if (userChart) userChart.destroy();

    const userHours = {};
    records.forEach(r => {
        const uid = r.short_id;
        userHours[uid] = (userHours[uid] || 0) + (r.duration_min || 0) / 60;
    });

    const sorted = Object.entries(userHours).sort((a, b) => b[1] - a[1]).slice(0, 8);
    const labels = sorted.map(([k]) => k);
    const data = sorted.map(([, v]) => Math.round(v * 10) / 10);

    userChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Hours",
                data,
                backgroundColor: "rgba(64, 196, 255, 0.4)",
                borderColor: "rgba(64, 196, 255, 0.8)",
                borderWidth: 1,
                borderRadius: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => `${ctx.raw}h` } }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: "Hours", color: "#888" },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y: {
                    grid: { color: "rgba(255,255,255,0.04)" },
                }
            }
        }
    });
}

function renderCalendar(records) {
    const container = document.getElementById("calendar-container");
    if (records.length === 0) {
        container.innerHTML = '<p style="text-align:center;padding:2rem;color:var(--text-muted);font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;">No data for calendar</p>';
        return;
    }
    const { from, to } = getDateRange();
    const startDate = new Date(from);
    const endDate = new Date(to);

    const dayCounts = {};
    records.forEach(r => {
        if (!r.start_time) return;
        const day = r.start_time.slice(0, 10);
        dayCounts[day] = (dayCounts[day] || 0) + 1;
    });

    const maxCount = Math.max(...Object.values(dayCounts), 1);

    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    let firstMonday = new Date(startDate);
    const dayOfWeek = firstMonday.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    firstMonday.setDate(firstMonday.getDate() + diff);

    const weeks = [];
    let current = new Date(firstMonday);
    while (current <= endDate) {
        const week = [];
        for (let i = 0; i < 7; i++) {
            const dateStr = current.toISOString().slice(0, 10);
            const inRange = current >= startDate && current <= endDate;
            week.push({
                date: dateStr,
                count: dayCounts[dateStr] || 0,
                inRange,
                dayLabel: current.toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
            });
            current.setDate(current.getDate() + 1);
        }
        weeks.push(week);
    }

    let html = '<div class="calendar-heatmap">';
    html += '<div class="calendar-body">';
    html += '<div class="calendar-day-labels">';
    dayNames.forEach(d => {
        html += `<div class="calendar-day-label">${d}</div>`;
    });
    html += '</div>';
    html += '<div class="calendar-weeks">';

    weeks.forEach(week => {
        html += '<div class="calendar-week-col">';
        week.forEach(day => {
            if (!day.inRange) {
                html += '<div class="calendar-cell" style="opacity:0.15"></div>';
                return;
            }
            const heatLevel = day.count === 0 ? 0 : Math.min(4, Math.ceil((day.count / maxCount) * 4));
            const heatClass = heatLevel > 0 ? `heat-${heatLevel}` : "";
            html += `<div class="calendar-cell ${heatClass}" data-count="${day.count}">`;
            html += `<span class="calendar-tooltip">${day.dayLabel}: ${day.count} session${day.count !== 1 ? 's' : ''}</span>`;
            html += '</div>';
        });
        html += '</div>';
    });

    html += '</div></div>';

    const legendHtml = `
        <div style="display:flex;align-items:center;gap:0.5rem;margin-top:1rem;padding-left:53px;">
            <span style="font-size:0.6rem;color:var(--text-muted);letter-spacing:0.08em;text-transform:uppercase">Less</span>
            <div class="calendar-cell" style="width:16px;height:16px;display:inline-block"></div>
            <div class="calendar-cell heat-1" style="width:16px;height:16px;display:inline-block"></div>
            <div class="calendar-cell heat-2" style="width:16px;height:16px;display:inline-block"></div>
            <div class="calendar-cell heat-3" style="width:16px;height:16px;display:inline-block"></div>
            <div class="calendar-cell heat-4" style="width:16px;height:16px;display:inline-block"></div>
            <span style="font-size:0.6rem;color:var(--text-muted);letter-spacing:0.08em;text-transform:uppercase">More</span>
        </div>
    `;

    html += legendHtml + '</div>';
    container.innerHTML = html;
}

document.getElementById("filter-period").addEventListener("change", function() {
    document.getElementById("filter-from").value = "";
    document.getElementById("filter-to").value = "";
    const { from, to } = getDateRange();
    document.getElementById("filter-from").value = from.slice(0, 10);
    document.getElementById("filter-to").value = to.slice(0, 10);
    fetchStatistics();
});

document.getElementById("filter-bench").addEventListener("change", fetchStatistics);
document.getElementById("filter-user").addEventListener("change", fetchStatistics);

document.addEventListener("DOMContentLoaded", () => {
    const { from, to } = getDateRange();
    document.getElementById("filter-from").value = from.slice(0, 10);
    document.getElementById("filter-to").value = to.slice(0, 10);
    fetchStatistics();

    document.querySelectorAll(".chart-panel").forEach(panel => {
        panel.addEventListener("click", () => openLightbox(panel));
    });
});

function openLightbox(panel) {
    const lightbox = document.getElementById("chart-lightbox");
    const content = document.getElementById("chart-lightbox-content");
    const canvas = panel.querySelector("canvas");

    if (!canvas) return;

    const imgUrl = canvas.toDataURL();
    content.innerHTML = `<img src="${imgUrl}" style="width:100%;height:100%;object-fit:contain;">`;
    lightbox.classList.add("active");
}

function closeLightbox(event) {
    const content = document.getElementById("chart-lightbox-content");
    if (event.target === content || content.contains(event.target)) return;

    const lightbox = document.getElementById("chart-lightbox");
    lightbox.classList.remove("active");
}

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        const lightbox = document.getElementById("chart-lightbox");
        lightbox.classList.remove("active");
    }
});
