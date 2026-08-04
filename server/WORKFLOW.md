# System Function Bench Tracker — Workflow Documentation

## Table of Contents
1. [System Startup Flow](#system-startup)
2. [Auto Check-in Flow (RDP Connect)](#auto-checkin)
3. [Auto Check-out Flow (RDP Disconnect)](#auto-checkout)
4. [Screen Lock Flow (Win+L)](#screen-lock)
5. [Dashboard Live Polling](#dashboard-polling)
6. [Request for Release Button](#request-release)
7. [Restart Button](#restart)
8. [Statistics Page](#statistics)
9. [History Page](#history)
10. [Bench Detail Page](#bench-detail)
11. [Defect Board (Jira Integration)](#defect-board)
12. [Session Monitor Watchdog](#watchdog)
13. [Server Startup](#server-startup)

---

## 1. System Startup Flow <a name="system-startup"></a>

### What happens when a bench PC boots/restarts:

```
┌──────────────────────────────────────────────────────────────┐
│                    BENCH PC BOOTS UP                           │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Windows Login Screen → User logs in                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Scheduled Task "BenchSessionMonitor" triggers (/sc onlogon)  │
│  Runs: pythonw.exe session_monitor.py                         │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Session Monitor starts:                                      │
│  1. Loads config.ini (bench_id, server_url)                   │
│  2. Waits 5 seconds (desktop to be ready)                     │
│  3. Launches login_gate.py                                    │
│  4. Starts WTS event listener (listens for RDP events)        │
│  5. Starts safety-net poller (backup detection every 5s)      │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Login Gate appears (fullscreen, cannot close):               │
│  - Rotating Mercedes logo                                     │
│  - Bench name (VIJAYANAGARA, MAURYA, etc.)                   │
│  - Short ID input                                             │
│  - Purpose dropdown                                           │
│  - CHECK IN & START button (white)                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Auto Check-in Flow (RDP Connect) <a name="auto-checkin"></a>

### What happens when someone connects via RDP:

```
┌──────────────────────────────────────────────────────────────┐
│  User connects via RDP to bench PC                            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Windows fires WTS event: REMOTE_CONNECT (0x3)                │
│  Session Monitor receives it                                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Session Monitor checks:                                      │
│  - Is login gate already running? (process check + lock file) │
│  - Was it launched in last 30 seconds? (debounce)             │
│  If NO → launches login_gate.py                               │
│  If YES → skips (prevents double)                             │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Login Gate appears on user's screen                          │
│  User enters: Short ID + Purpose                              │
│  Clicks "CHECK IN & START"                                    │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Button turns GREEN, text changes to "Checking in..."         │
│  Background thread sends:                                     │
│  POST /api/checkin                                            │
│  {                                                            │
│    "bench_id": 2,                                             │
│    "pc_type": "windows",                                      │
│    "short_id": "ADPRIYA",                                     │
│    "purpose": "Software Debug",                               │
│    "access_method": "rdp"                                     │
│  }                                                            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Server receives checkin:                                     │
│  1. Validates input (Pydantic model)                          │
│  2. If bench already occupied → checkout first                │
│  3. Marks WINDOWS as occupied in bench_status                 │
│  4. Marks LINUX as occupied (same user, same purpose)         │
│  5. Returns 200 OK                                            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Login Gate closes (after 300ms)                              │
│  User can now use the bench                                   │
│  Dashboard updates within 5 seconds (next poll)               │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Auto Check-out Flow (RDP Disconnect) <a name="auto-checkout"></a>

### What happens when someone disconnects RDP:

```
┌──────────────────────────────────────────────────────────────┐
│  User closes RDP / disconnects                                │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Windows fires: CONSOLE_DISCONNECT (0x2)                      │
│  Session Monitor receives it                                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Delayed Disconnect Check (background thread):                │
│  1. Wait 5 seconds (avoid false triggers during handshake)    │
│  2. Call is_session_disconnected() — checks WTS session state │
│  3. If session is TRULY disconnected AND was active:          │
│     → Send checkout                                           │
│  4. If session reconnected during wait:                       │
│     → Do nothing (was just a handshake)                       │
└─────────────────────────────┬────────────────────────────────┘
                              │ (if confirmed disconnected)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  POST /api/checkout                                           │
│  {"bench_id": 2, "pc_type": "windows"}                       │
│  (proxies=NO_PROXY to bypass corporate proxy)                 │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Server receives checkout:                                    │
│  1. Sets WINDOWS bench_status → available                     │
│  2. Sets LINUX bench_status → available                       │
│  3. Calculates duration                                       │
│  4. Moves session to usage_history table                      │
│  5. Returns 200 OK                                            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Dashboard updates within 5 seconds (next poll)               │
│  Bench card shows "Available" with green badge                │
│  Toast notification: "ADPRIYA checked out — Maurya"           │
└──────────────────────────────────────────────────────────────┘
```

### Safety-Net Poller (Backup):
```
If WTS events fail to fire (rare edge case):
  - Safety-net poller runs every 5 seconds
  - Skips if WTS event happened in last 10 seconds (avoids conflicts)
  - Calls is_session_disconnected() directly
  - If disconnected AND _session_active → sends checkout
  - If reconnected AND NOT _session_active → launches login gate
```

---

## 4. Screen Lock Flow (Win+L) <a name="screen-lock"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User presses Win+L (locks screen)                            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Windows fires: SESSION_LOCK (0x7)                            │
│  This IS in RELEASE_EVENTS                                    │
│  → Sends checkout immediately                                 │
│  → Dashboard shows bench as Available                         │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼ (when user unlocks)
┌──────────────────────────────────────────────────────────────┐
│  Windows fires: SESSION_UNLOCK (0x8)                          │
│  This IS in RESUME_EVENTS                                     │
│  → Launches login gate                                        │
│  → User must check in again                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Dashboard Live Polling <a name="dashboard-polling"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User opens http://c623drd41380439:8000/                      │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Page loads:                                                  │
│  1. HTML rendered (dashboard.html)                            │
│  2. CSS loaded (dashboard.css)                                │
│  3. JS loaded (dashboard.js)                                  │
│  4. Cards animate in (staggered fadeInUp)                     │
│  5. Mercedes logo rotates on load                             │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  fetchBenches() called immediately + every 5 seconds:         │
│                                                               │
│  GET /api/benches → returns all bench data                    │
│       │                                                       │
│       ▼                                                       │
│  buildStatusMap() → track which benches changed               │
│       │                                                       │
│       ▼                                                       │
│  detectAndNotify() → show toast if status changed             │
│       │                                                       │
│       ▼                                                       │
│  renderDashboard() → only re-render CHANGED cards (flip anim) │
│       │                                                       │
│       ▼                                                       │
│  updateStats() → update Available/Occupied/Users counters     │
└──────────────────────────────────────────────────────────────┘

Every 1 second:
  updateTimers() → update all running timers
  → Timer color: white (0-15m) → yellow (15-30m) → orange (30-45m) → red (60m+)
```

---

## 6. Request for Release Button <a name="request-release"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User sees an OCCUPIED bench on dashboard                     │
│  Clicks "🔔 Request" button                                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Modal dialog opens (centered, blurred background):           │
│  ┌────────────────────────────────────────┐                   │
│  │      REQUEST FOR RELEASE               │                   │
│  │                                        │                   │
│  │  Bench:    [MAURYA] (readonly)         │                   │
│  │  Requester: [dropdown - all users]     │                   │
│  │  Purpose:  [dropdown - purposes]       │                   │
│  │                                        │                   │
│  │        [ SEND REQUEST ]                │                   │
│  └────────────────────────────────────────┘                   │
└─────────────────────────────┬────────────────────────────────┘
                              │ (user fills and clicks Send)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  JavaScript:                                                  │
│  1. Gets occupant's email from benchData                      │
│  2. Constructs Teams deep link URL:                           │
│     https://teams.microsoft.com/l/chat/0/0?                   │
│     users=<occupant_email>&                                   │
│     message=Hi <name>, I need <bench> bench for <purpose>.    │
│             In how much time will it be free?                  │
│  3. Opens Teams URL (window.open)                             │
│  4. Closes modal                                              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Teams opens with pre-typed message                           │
│  User hits Send in Teams                                      │
│  Occupant receives DM notification                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Restart Button <a name="restart"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User sees an AVAILABLE bench on dashboard                    │
│  (Restart only shows for available benches)                   │
│  Clicks "🔄 Restart" button                                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Confirmation dialog opens (centered, blurred background):    │
│  ┌────────────────────────────────────────┐                   │
│  │        CONFIRM RESTART                 │                   │
│  │                                        │                   │
│  │  Are you sure you want to restart      │                   │
│  │  VIJAYANAGARA?                         │                   │
│  │                                        │                   │
│  │  ⚠ Any unsaved data will be lost.     │                   │
│  │                                        │                   │
│  │  [CANCEL] [WINDOWS] [LINUX]            │                   │
│  └────────────────────────────────────────┘                   │
└─────────────────────────────┬────────────────────────────────┘
                              │ (user clicks WINDOWS or LINUX)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  1. WINDOWS and LINUX buttons disabled instantly               │
│  2. Shows "Restarting windows..." message                     │
│  3. CANCEL stays enabled                                      │
│  4. Sends: POST /api/restart-bench                            │
│     {"bench_id": 1, "pc_type": "windows"}                    │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Server:                                                      │
│  1. Validates bench exists                                    │
│  2. Checks bench is NOT occupied (blocks if occupied)         │
│  3. Gets hostname from benches.json                           │
│  4. Gets credentials from credentials.json                    │
│  5. If WINDOWS:                                               │
│     → net rpc shutdown -r -f -I <hostname> -U <user>%<pass>  │
│  6. If LINUX:                                                 │
│     → sshpass -p <pass> ssh <user>@<host> "echo <pass> |     │
│       sudo -S reboot"                                         │
│  7. Returns 200 OK or 500 error                               │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Dialog closes instantly                                      │
│  Toast notification: "Restart signal sent — Windows"          │
│  Bench PC reboots                                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Statistics Page <a name="statistics"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User navigates to /statistics                                │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  On page load:                                                │
│  1. Default filter: Last 7 Days                               │
│  2. Date inputs auto-filled with from/to dates                │
│  3. Calls: GET /api/statistics?date_from=...&date_to=...      │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Server:                                                      │
│  1. Queries usage_history with date filters                   │
│  2. Filters to pc_type='windows' only (no duplicates)         │
│  3. Calculates summary (total sessions, avg duration, etc.)   │
│  4. Returns summary + records                                 │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Frontend renders:                                            │
│  1. Summary cards (Total Sessions, Avg Duration, etc.)        │
│  2. Peak Hours chart (bar chart - sessions by hour)           │
│  3. Daily Sessions chart (bar chart - sessions by day)        │
│  4. Usage by Bench (pie chart with connectors)                │
│  5. Usage by User (horizontal bar chart)                      │
│  6. Calendar Heatmap                                          │
└──────────────────────────────────────────────────────────────┘

User interactions:
  - Change period dropdown → dates auto-update → charts re-render
  - Change bench filter → re-fetch with bench_id param
  - Change user filter → re-fetch with short_id param
  - Click on chart panel → lightbox opens (zoomed view)
  - Click outside lightbox / press Escape → closes
```

---

## 9. History Page <a name="history"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User navigates to /history                                   │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  On page load:                                                │
│  1. Loads user map: GET /api/users                            │
│  2. Fetches history: GET /api/history?limit=200               │
│  3. Renders table with bench names, user + full name,         │
│     purpose, start/end time, duration                         │
└──────────────────────────────────────────────────────────────┘

User interactions:
  - Bench dropdown → re-fetches with bench_id filter
  - Short ID search → filters client-side (startsWith match)
  - Export CSV → downloads all displayed data as .csv file
  - Row hover → blue highlight
```

---

## 10. Bench Detail Page <a name="bench-detail"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User clicks on bench card header (or navigates to /bench/1)  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Fetches: GET /api/bench/1                                    │
│  Returns: name, architecture, sw_version, hostnames, IPs,     │
│           current status of windows + linux PCs               │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Page displays:                                               │
│  - Bench name + architecture badge + SW version               │
│  - Windows PC card (hostname, IP, status, user info)          │
│  - Linux PC card (hostname, IP, status)                       │
│  - Two tabs: [Usage History] [Statistics]                     │
│  - Range buttons: [Today] [Yesterday] [7 Days] [30 Days]     │
└──────────────────────────────────────────────────────────────┘

Tab: Usage History
  - Shows table filtered to this bench only
  - Range buttons filter by date

Tab: Statistics
  - Peak Hours chart (this bench only)
  - Daily Sessions chart (this bench only)
  - Usage by User chart (this bench only)
  - Range buttons re-render charts

Auto-refresh: bench status updates every 10 seconds
```

---

## 11. Defect Board (Jira Integration) <a name="defect-board"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  User navigates to /defect-board                              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Page loads:                                                  │
│  1. HTML rendered (defect_board.html)                         │
│  2. CSS loaded (defect_board.css)                             │
│  3. JS loaded (defect_board.js)                               │
│  4. loadAll() fires immediately:                              │
│     - GET /api/jira/overview                                  │
│     - GET /api/jira/by-sysfunc                                │
│     - GET /api/jira/list?status=open                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Server (jira_routes.py):                                     │
│  1. JiraClient reads jira_config.json (base_url, email, token)│
│  2. Builds JQL query:                                         │
│     project = ADASDAI AND issuetype = Bug                     │
│     AND labels = "SYS4_Bench_Test"                            │
│     AND labels in (Dimming, PRD, GTS, POM, ...)              │
│  3. Calls Jira REST API: /rest/api/3/search/jql              │
│  4. Maps raw Jira JSON → simplified objects                   │
│  5. Caches results for 180 seconds                            │
│  6. Returns JSON to frontend                                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Frontend renders:                                            │
│  1. Stats cards: Total Bugs | Ongoing (blue) | Closed (green) │
│  2. Donut chart: Ongoing status distribution                  │
│  3. Bar chart: Module wise distribution (orange bars)          │
│  4. Category tabs: Parking | Miscellaneous | etc.             │
│  5. SysFunc table: Acronym, Name, Ongoing, Closed, Total      │
│  6. Defect list table: Key, Status, Priority, Summary, etc.   │
│  7. Pagination: Prev | Page X of Y | Next                     │
└──────────────────────────────────────────────────────────────┘

Auto-refresh: every 120 seconds (silent, no loading spinner)
Page Visibility: refresh on tab focus, full reload after 10min hidden
Live indicator: green dot + "Updated: Xs ago" in header

User interactions:
  - Filter dropdowns: Release Version, Release Candidate, Safety Type
  - Apply button: re-fetches with selected filters
  - Reset button: clears all filters
  - Refresh button: clears cache + re-fetches
  - Category tab click: filters sysfunc table + defect list
  - SysFunc row click: filters defect list to that sysfunc only
  - Defect key link: opens in Jira (new tab)
  - Pagination: Prev/Next buttons for defect list
```

### Jira Data Flow:
```
jira_config.json → JiraClient → Jira REST API → map_issue() → Cache → API Response → Frontend
     │                  │              │                │          │
  credentials      auth=(email,    GET /rest/api/    simplify    180s TTL
                   token)          3/search/jql     JSON fields
```

### Filters (JQL Construction):
```
Base:     project = ADASDAI AND issuetype = Bug AND labels = "SYS4_Bench_Test"
+ Release:       AND labels = "R18"
+ Candidate:     AND labels = "MF4"
+ Safety:        AND labels = "FUSA"
+ SysFunc:       AND labels = "DLLR"
+ Status open:   AND status != "Closed"
+ Sort:          ORDER BY priority DESC, updated DESC
```

---

## 12. Session Monitor Watchdog <a name="watchdog"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  Session Monitor main loop with watchdog:                     │
│                                                               │
│  while restart_count < 50:                                    │
│      try:                                                     │
│          load_config()                                        │
│          launch_login_gate()                                  │
│          start WTS event monitoring                           │
│          ← runs indefinitely until crash                      │
│      except Exception:                                        │
│          restart_count += 1                                   │
│          log error                                            │
│          wait 10 seconds                                      │
│          ← loop back and restart                              │
│                                                               │
│  If max restarts (50) reached → stop completely               │
└──────────────────────────────────────────────────────────────┘

This ensures:
  - If monitor crashes (any unhandled exception) → auto-restarts in 10s
  - Up to 50 restarts before giving up
  - Every restart re-loads config, re-launches login gate
```

---

## 12. Server Startup <a name="server-startup"></a>

```
┌──────────────────────────────────────────────────────────────┐
│  Server PC boots / uvicorn started                            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  uvicorn loads main.py:                                       │
│  1. Creates FastAPI app                                       │
│  2. Adds CORS middleware                                      │
│  3. Mounts /static directory                                  │
│  4. Registers route modules (bench_routes, history_routes)    │
│  5. On startup event: init_db()                               │
│     → Creates bench_status table (if not exists)              │
│     → Creates usage_history table (if not exists)             │
│     → Seeds 10 rows in bench_status (5 benches × 2 pc_types) │
│  6. Starts listening on 0.0.0.0:8000                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Server ready:                                                │
│  - Accepts HTTP requests from bench PCs (checkin/checkout)    │
│  - Serves dashboard to browsers                               │
│  - Handles restart commands                                   │
│  - Reads config files on each relevant request                │
└──────────────────────────────────────────────────────────────┘
```

---

## Event Reference Table

### WTS Session Events (Windows)

| Event Code | Name | Action |
|---|---|---|
| 0x1 | CONSOLE_CONNECT | → Launch login gate |
| 0x2 | CONSOLE_DISCONNECT | → Delayed verify (5s) then checkout |
| 0x3 | REMOTE_CONNECT (RDP) | → Launch login gate |
| 0x4 | REMOTE_DISCONNECT (RDP) | → Checkout immediately |
| 0x5 | SESSION_LOGON | → Launch login gate |
| 0x6 | SESSION_LOGOFF | → Checkout immediately |
| 0x7 | SESSION_LOCK (Win+L) | → Checkout immediately |
| 0x8 | SESSION_UNLOCK | → Launch login gate |

### Debounce & Timing

| Timer | Value | Purpose |
|---|---|---|
| Login gate debounce | 30 seconds | Prevent double launch |
| Checkout debounce | 10 seconds | Prevent double checkout |
| Disconnect verify delay | 5 seconds | Confirm real disconnect |
| Safety-net WTS cooldown | 10 seconds | Don't conflict with WTS events |
| Safety-net poll interval | 5 seconds | Backup detection speed |
| Dashboard poll interval | 5 seconds | UI refresh rate |
| Watchdog restart delay | 10 seconds | Wait before auto-restart |

---

## File Dependency Map

```
session_monitor.py
    ├── reads: config.ini (bench_id, server_url)
    ├── launches: login_gate.py
    ├── calls: POST /api/checkin (via login_gate.py)
    ├── calls: POST /api/checkout (directly)
    └── uses: pywin32 (WTS events), requests (HTTP)

login_gate.py
    ├── reads: config.ini (bench_id, server_url)
    ├── reads: MBRDI.png (logo for rotation)
    ├── calls: POST /api/checkin
    ├── writes: local_checkins.json (fallback if server offline)
    ├── writes: .login_gate.lock (prevent duplicates)
    └── uses: tkinter (UI), PIL/Pillow (logo rotation), requests (HTTP)

server/main.py
    ├── imports: routes/bench_routes.py
    ├── imports: routes/history_routes.py
    ├── imports: routes/jira_routes.py
    ├── imports: database.py
    ├── serves: templates/*.html
    └── serves: static/* (CSS, JS, images)

bench_routes.py
    ├── reads: config/benches.json
    ├── reads: config/users.json
    ├── reads: config/credentials.json
    ├── calls: database.py functions
    └── executes: net rpc / sshpass (restart)

jira_routes.py
    ├── reads: config/jira_config.json (credentials)
    ├── calls: Jira REST API (https://mercedes-benz.atlassian.net)
    ├── uses: httpx (async HTTP client)
    ├── caches: in-memory with 180s TTL
    └── serves: /api/jira/overview, /api/jira/by-sysfunc, /api/jira/list

dashboard.js
    ├── polls: GET /api/benches (every 5s)
    ├── calls: GET /api/users (for modals)
    ├── calls: GET /api/history (history page)
    ├── calls: POST /api/restart-bench
    └── opens: Teams deep link (request release)

defect_board.js
    ├── polls: GET /api/jira/overview (every 120s)
    ├── polls: GET /api/jira/by-sysfunc (every 120s)
    ├── polls: GET /api/jira/list (every 120s)
    ├── calls: GET /api/jira/cache-clear (on Refresh click)
    └── uses: Chart.js (donut + bar charts)
```
