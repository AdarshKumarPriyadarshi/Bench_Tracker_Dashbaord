# System Function Bench Tracker — Complete Architecture & Documentation

## Project Overview

**System Function Bench Tracker** is a real-time dashboard for tracking 5 shared open-loop test benches at Mercedes-Benz Research & Development India (MBRDI). It automates bench check-in/check-out via Windows session event detection, provides remote restart capability, usage statistics, and integrates with Jira for defect tracking.

**Key Facts:**
- 5 test benches shared across 15+ engineers
- Auto check-in on RDP connect (mandatory login gate)
- Auto release on RDP disconnect
- Live dashboard with 5-second polling
- Remote restart (Windows + Linux)
- Usage statistics and analytics
- Jira defect board integration

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CORPORATE NETWORK                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  BENCH PC (x5)  │  CLIENT LAYER (Windows 11)                              │
│  │                  │                                                         │
│  │  session_monitor │         ┌────────────────────────────────────┐          │
│  │  login_gate      │──POST──▶│                                    │          │
│  │  startup_cleanup │──POST──▶│      FASTAPI SERVER                │          │
│  │                  │         │      (c623drd41380439:8000)         │          │
│  └─────────────────┘         │      Ubuntu Linux                   │          │
│                               │                                    │          │
│  ┌─────────────────┐         │  ┌──────────┐  ┌───────────────┐  │          │
│  │  BROWSER (x15+) │         │  │  Routes   │  │  SQLite DB    │  │          │
│  │  Dashboard      │──GET───▶│  │           │  │  bench_data.db│  │          │
│  │  Polls /5sec    │         │  │  bench_   │  │               │  │          │
│  │                  │◀──JSON──│  │  history_ │  │  bench_status │  │          │
│  │  Defect Board   │         │  │  jira_    │  │  usage_history│  │          │
│  │  Polls /120sec  │         │  │  routes   │  └───────────────┘  │          │
│  └─────────────────┘         │  └──────────┘                      │          │
│                               │                                    │          │
│                               │  ┌──────────────────────────────┐  │          │
│  ┌─────────────────┐         │  │  External APIs               │  │          │
│  │  JIRA CLOUD     │◀──GET───│  │  Jira REST API v3            │  │          │
│  │  (atlassian.net)│         │  │  (httpx async client)         │  │          │
│  └─────────────────┘         │  └──────────────────────────────┘  │          │
│                               └────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete File Structure

```
Bench_Info_Automation/
├── server/                              # SERVER (Linux PC: c623drd41380439)
│   ├── app/
│   │   ├── main.py                      # FastAPI app entry point
│   │   ├── database.py                  # SQLite CRUD operations
│   │   ├── models.py                    # Pydantic request validation
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── bench_routes.py          # Checkin/Checkout/Restart/Release APIs
│   │   │   ├── history_routes.py        # History/Statistics APIs
│   │   │   └── jira_routes.py           # Jira Defect Board APIs
│   │   ├── templates/
│   │   │   ├── dashboard.html           # Main dashboard page
│   │   │   ├── history.html             # Usage history page
│   │   │   ├── statistics.html          # Statistics/analytics page
│   │   │   ├── bench_detail.html        # Individual bench detail
│   │   │   └── defect_board.html        # Jira Defect Board page
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   ├── dashboard.css        # Main stylesheet (dark theme)
│   │   │   │   ├── bench_detail.css     # Bench detail styles
│   │   │   │   ├── statistics.css       # Statistics page styles
│   │   │   │   └── defect_board.css     # Defect Board styles
│   │   │   ├── js/
│   │   │   │   ├── dashboard.js         # Dashboard + History logic
│   │   │   │   ├── statistics.js        # Statistics charts (Chart.js)
│   │   │   │   ├── defect_board.js      # Defect Board logic
│   │   │   │   ├── chart.umd.min.js     # Chart.js library (local)
│   │   │   │   └── chartjs-adapter-date-fns.bundle.min.js
│   │   │   └── MBRDI.png               # Mercedes logo
│   │   └── bench_data.db               # SQLite database (DO NOT DELETE)
│   ├── config/
│   │   ├── benches.json                 # Bench metadata
│   │   ├── users.json                   # User directory
│   │   ├── credentials.json             # Restart credentials
│   │   └── jira_config.json             # Jira API credentials
│   ├── requirements.txt                 # Python dependencies
│   ├── setup_server.sh                  # Server setup script
│   ├── run_server.sh                    # Server start script
│   ├── API_DOCUMENTATION.md             # API reference
│   └── WORKFLOW.md                      # Workflow diagrams
│
├── client_windows/                      # CLIENT (per bench PC)
│   ├── session_monitor.py               # Background session event detection
│   ├── login_gate.py                    # Fullscreen check-in form (Tkinter)
│   ├── startup_cleanup.py               # Boot-time cleanup (SYSTEM)
│   ├── setup_client.bat                 # Windows setup script
│   ├── requirements.txt                 # Client dependencies
│   ├── MBRDI.png                        # Logo for login gate
│   └── Steps_to_setup.txt              # Setup instructions
│
├── client_linux/                        # LINUX CLIENT (legacy)
│   ├── session_monitor.py
│   ├── login_gate.py
│   ├── setup_client.sh
│   └── Steps_to_setup.txt
│
├── jira/                                # STANDALONE JIRA PROJECT (reference)
│   ├── backend/                         # FastAPI + httpx (Jira API)
│   └── frontend/                        # Next.js 16 + React 19 + Tailwind 4
│
├── drburn-7.1.6/                        # DR. BURN TOOL (modified)
│   └── src/drburn.py                    # Auto-updates dashboard after flash
│
└── Task.txt                             # Deployment commands
```

---

## Server — File by File

### main.py — Application Entry Point

**What it does:** Creates FastAPI app, adds middleware, mounts static files, registers routes, initializes database.

**Key parts:**
- `CORSMiddleware` — restricts to `http://c623drd41380439:8000` and `http://localhost:8000`
- `StaticFiles` mount at `/static`
- `Jinja2Templates` from `templates/` directory
- Registers: `bench_router`, `history_router`, `jira_router`
- `@app.on_event("startup")` → calls `db.init_db()`
- Page routes: `/`, `/history`, `/statistics`, `/bench/{bench_id}`, `/defect-board`

**To modify:** Add new page routes, change CORS origins, register new route modules.

---

### database.py — SQLite Operations

**What it does:** All database CRUD. Uses WAL mode for concurrent reads.

**Functions:**
| Function | Purpose |
|----------|---------|
| `get_connection()` | Returns SQLite connection with WAL mode + row_factory |
| `init_db()` | Creates tables, seeds 10 rows (5 benches × 2 pc_types) |
| `checkin(bench_id, pc_type, short_id, purpose, access_method)` | UPDATE bench_status → occupied |
| `checkout(bench_id, pc_type)` | INSERT usage_history + UPDATE bench_status → available |
| `get_all_benches()` | SELECT * FROM bench_status |
| `get_history(bench_id, short_id, limit, date_from, date_to)` | SELECT from usage_history with filters |

**Tables:**
```sql
-- Current state (10 rows always)
bench_status (bench_id, pc_type, status, short_id, purpose, access_method, start_time)
PRIMARY KEY (bench_id, pc_type)

-- Historical sessions (grows over time)
usage_history (id AUTOINCREMENT, bench_id, pc_type, short_id, purpose, access_method, start_time, end_time, duration_min)
```

**To modify:** Add new tables, add fields to existing tables, change query logic.

---

### models.py — Request Validation

**What it does:** Pydantic models for all POST request bodies. Auto-validates and rejects bad input.

**Models:**
| Model | Fields | Used by |
|-------|--------|---------|
| `CheckinRequest` | bench_id(1-5), pc_type, short_id(regex), purpose(HTML stripped), access_method | POST /api/checkin |
| `CheckoutRequest` | bench_id(1-5), pc_type | POST /api/checkout |
| `ReleaseRequest` | bench_id(1-5), requester_id(regex), purpose(HTML stripped) | POST /api/request-release |
| `RestartRequest` | bench_id(1-5), pc_type | POST /api/restart-bench |

**Security features:**
- `strip_html()` removes `<script>` and other HTML tags from purpose field
- Regex pattern `^[A-Za-z0-9_]+$` for short_id (no special chars)
- Length limits on all string fields

**To modify:** Add new request models, change validation rules, add fields.

---

### routes/bench_routes.py — Core Bench APIs

**What it does:** All bench check-in/check-out, restart, release request, SW update endpoints.

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/checkin` | POST | Mark bench occupied (both Windows + Linux) |
| `/api/checkout` | POST | Release bench (both Windows + Linux), save history |
| `/api/benches` | GET | Return all bench status + metadata from config |
| `/api/bench/{id}` | GET | Single bench detail |
| `/api/request-release` | POST | Log release request, return occupant info |
| `/api/restart-bench` | POST | Execute remote restart (net rpc / sshpass) |
| `/api/update-bench-sw` | POST | Update SW version in benches.json |
| `/api/users` | GET | Return all registered users |
| `/api/health` | GET | Health check |

**Key logic:**
- Checkin auto-checkouts previous user if bench already occupied
- Checkin marks BOTH Windows + Linux as occupied (unified tracking)
- Checkout marks BOTH as available, inserts BOTH into history
- Restart blocked if bench is occupied
- Restart uses `credentials.json` with per-bench overrides

**To modify:** Add new endpoints, change business logic, add new config reads.

---

### routes/history_routes.py — History & Statistics APIs

**What it does:** Serves usage history and aggregated statistics.

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/history` | GET | Paginated history (filtered to windows only) |
| `/api/statistics` | GET | Aggregated stats: sessions, duration, top user, etc. |

**Key logic:**
- Both endpoints filter to `pc_type='windows'` to avoid double-counting
- Statistics default: last 7 days, limit 2000 records
- Calculates: total_sessions, avg_duration, most_used_bench, top_user, busiest_day

**To modify:** Add new stats calculations, change default date range, add filters.

---

### routes/jira_routes.py — Jira Defect Board APIs

**What it does:** Fetches defect data from Jira Cloud REST API, caches it, serves to the defect board page.

**Architecture (same pattern as standalone jira/ project):**
```python
class JiraClient:
    def __init__(self):         # Reads jira_config.json
    def _client(self):          # Returns httpx.AsyncClient
    async def search_issues():  # GET /rest/api/3/search/jql
```

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jira/overview` | GET | Total, ongoing, closed, aging, priorities, status distribution |
| `/api/jira/by-sysfunc` | GET | Defect counts per system function |
| `/api/jira/list` | GET | Paginated defect list (filtered) |
| `/api/jira/cache-clear` | GET | Clear in-memory cache |

**Data flow:**
```
jira_config.json → JiraClient → Jira REST API → map_issue() → Cache (180s) → JSON response
```

**JQL query built by `build_base_jql()`:**
```
project = ADASDAI AND issuetype = Bug AND labels = "SYS4_Bench_Test"
AND labels in (Dimming, PRD, GTS, POM, PDD, PSSDS, DLCS, DLLR, ...)
[+ optional: AND labels = "R18"]
[+ optional: AND labels = "MF4"]
[+ optional: AND labels = "FUSA"]
ORDER BY priority DESC, updated DESC
```

**System Functions tracked (21 total):**
Dimming, PRD, GTS, POM, PDD, PSSDS, DLCS, DLLR, SSPN, SEM_ROV, ODF, Presafe, Visualisation, CCHP, PTS_Op_Mode, SVS_Op_Mode, ALSA, PWD, AR, VRP, VBPS

**Categories:** Parking, Miscellaneous, Driving Function, ODF, ROV Functions Contributions

**To modify:** Change JQL query, add/remove system functions, change status colors, modify cache TTL.

---

## Client — File by File

### session_monitor.py — Background Session Detection

**What it does:** Runs silently on each bench PC, detects Windows session events (RDP connect/disconnect, lock, logoff), triggers check-in gate or sends checkout.

**Core mechanism:**
```python
# Creates hidden window, registers for WTS notifications
win32ts.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_ALL_SESSIONS)
# Blocks on message pump, receives WM_WTSSESSION_CHANGE events
win32gui.PumpMessages()
```

**Event handling:**
| Event | Action |
|-------|--------|
| REMOTE_CONNECT (0x3) | Launch login gate |
| REMOTE_DISCONNECT (0x4) | Send checkout immediately |
| SESSION_LOCK (0x7) | Send checkout immediately |
| SESSION_UNLOCK (0x8) | Launch login gate |
| SESSION_LOGON (0x5) | Launch login gate |
| SESSION_LOGOFF (0x6) | Send checkout immediately |
| CONSOLE_CONNECT (0x1) | Launch login gate |
| CONSOLE_DISCONNECT (0x2) | Delayed 5s verify → checkout |

**Safety mechanisms (8 layers):**
1. **Debounce 30s** — no double login gate
2. **is_login_gate_running()** — lock file + WMIC process check
3. **_last_lock_time 15s** — ignore resume events after Win+L
4. **Delayed disconnect 5s** — avoid false checkout during RDP handshake
5. **Checkout debounce 10s** — no duplicate checkout
6. **Watchdog MAX_RESTARTS=50** — auto restart on crash
7. **is_another_monitor_running()** — prevent duplicate monitors
8. **startup_cleanup.py** — clear stale state on boot

**Safety-net poller (backup thread):**
- Runs every 5 seconds
- Skips if WTS event received in last 10s
- Checks `WTSEnumerateSessions` for actual session state
- Catches events missed by message pump

**To modify:** Change debounce times, add/remove events, modify detection logic.

---

### login_gate.py — Fullscreen Check-in Form

**What it does:** Shows an unclosable fullscreen Tkinter window forcing user to identify themselves.

**UI elements:**
- Rotating Mercedes logo (PIL/Pillow, 36 frames at 50ms interval)
- Bench name (VIJAYANAGARA, MAURYA, etc.)
- PC type badge (WINDOWS PC) + Access method badge (RDP/PHYSICAL)
- Short ID text entry
- Purpose dropdown (Combobox, also allows free text)
- CHECK IN & START button (white → green on click)
- Error label (red text)

**Key features:**
- `root.attributes("-fullscreen", True)` — covers entire screen
- `root.attributes("-topmost", True)` — always on top
- `root.protocol("WM_DELETE_WINDOW", block)` — blocks X button
- `root.bind("<Alt-F4>", block)` — blocks Alt+F4
- `root.grab_set()` — captures all input
- Threading for HTTP call (prevents "Not Responding")
- Lock file (`.login_gate.lock`) with PID for duplicate prevention
- Falls back to `local_checkins.json` if server offline

**Purpose list:**
Automation Execution, Automation Integration, Bench Debugging (HW), Software Flashing, Diagnostic (SEM) Testing, Execution Analysis, Log Collection, Manual Execution, Night Run Execution - DND, Software Debugging

**To modify:** Change purposes list, modify UI layout, add fields, change colors.

---

### startup_cleanup.py — Boot-time Cleanup

**What it does:** Runs as SYSTEM on boot (before any user logs in). Ensures dashboard releases bench even if PC rebooted without proper checkout.

**Actions:**
1. Delete `.session_monitor.lock`
2. Delete `.login_gate.lock`
3. Wait 10 seconds (network readiness)
4. Send `POST /api/checkout` to release bench on dashboard

**Runs as:** SYSTEM account (no GUI, no user session needed)
**Trigger:** Scheduled task `BenchStartupCleanup` with `/sc onstart`

**To modify:** Change delay, add more cleanup tasks, add logging.

---

## Frontend — File by File

### dashboard.js — Dashboard + History Logic

**What it does:** Polls server, renders bench cards, handles notifications, modals, history table.

**Key functions:**
| Function | Purpose |
|----------|---------|
| `fetchBenches()` | GET /api/benches, detect changes, re-render |
| `renderBenchCard(win, lin)` | Generate HTML for one bench card |
| `renderDashboard(changedSlots)` | Only re-render changed cards (flip animation) |
| `updateTimers()` | Update all running timers every 1s, color-code by duration |
| `updateStats()` | Animate stat counter changes |
| `detectAndNotify(old, new)` | Show toast + browser notification on status change |
| `confirmRestart(benchId, name)` | Show restart confirmation dialog |
| `sendRestart(pcType)` | POST /api/restart-bench |
| `openReleaseModal(benchId, name)` | Show request-for-release dialog |
| `sendReleaseRequest()` | Open Teams deep link with pre-typed message |
| `manualRelease(benchId)` | POST /api/checkout (for physical access users) |
| `fetchHistory()` | GET /api/history, render table |
| `exportCSV()` | Download history as CSV |

**Polling cycle:**
```
DOMContentLoaded → fetchBenches() + setInterval(5000)
                 → setInterval(updateTimers, 1000)
                 → setInterval(updateLastUpdated, 1000)
```

**Page Visibility API:**
- Hidden > 10 min → full page reload
- Hidden < 10 min → instant fetchBenches() on return

**Purple flashing card:** When purpose includes "flashing", card gets purple animated class.

**To modify:** Change polling interval, add UI elements, modify modals, change timer colors.

---

### defect_board.js — Jira Defect Board Logic

**What it does:** Fetches Jira data from our API, renders charts and tables.

**Key functions:**
| Function | Purpose |
|----------|---------|
| `loadAll()` | Fetch overview + sysfunc + defect list in parallel |
| `loadOverview()` | GET /api/jira/overview, render stats + donut |
| `loadSysfunc()` | GET /api/jira/by-sysfunc, render tabs + table + bar chart |
| `loadDefectList()` | GET /api/jira/list, render defect table + pagination |
| `renderStatusDonut()` | Chart.js doughnut (ongoing status distribution) |
| `renderModuleBarChart()` | Chart.js vertical bar (module wise distribution) |
| `renderCategoryTabs()` | Category filter buttons with counts |
| `renderSysfuncTable()` | SysFunc summary table |
| `renderDefectList()` | Paginated defect list with Jira links |
| `applyFilters()` | Re-fetch with selected filter values |
| `resetFilters()` | Clear all dropdowns, reload |
| `refreshData()` | Clear cache + reload |
| `selectCategory(cat)` | Filter by category tab |
| `selectSysfunc(acronym)` | Filter by specific system function |

**Auto-refresh:** Every 120 seconds (silent, no loading spinner after first load)
**Page Visibility:** Same as dashboard (refresh on focus, reload after 10min)
**Live indicator:** Green dot + "Updated: Xs ago"
**Offline banner:** Red banner if API fails

**To modify:** Change refresh interval, add charts, modify filter options.

---

### statistics.js — Statistics Charts

**What it does:** Renders Chart.js charts for usage analytics.

**Charts rendered:**
1. Peak Hours (bar — sessions by hour of day)
2. Daily Sessions (bar — sessions by date)
3. Usage by Bench (pie with connector labels)
4. Usage by User (horizontal bar)
5. Calendar Heatmap (custom HTML rendering)

**To modify:** Add new charts, change colors, modify date logic.

---

## Configuration Files

### benches.json
```json
{
    "benches": [
        {
            "bench_id": 1,
            "name": "Vijayanagara",
            "architecture": "ST3",
            "sw_version": "R18.6.3",
            "windows_hostname": "CGSCLXR85387250",
            "windows_ip": "53.217.60.187",
            "linux_hostname": "C623LRD90775115",
            "linux_ip": "53.217.60.174"
        }
    ]
}
```
**Modify to:** Add/rename benches, update SW version, change hostnames/IPs.

### users.json
```json
{
    "users": {
        "ADPRIYA": {"name": "Adarsh Priyadarshi", "email": "adarsh.priyadarshi@mercedes-benz.com"}
    }
}
```
**Modify to:** Add/remove users. No server restart needed.

### credentials.json
```json
{
    "windows": {
        "default": {"username": "PIDDB58", "password": "External@12345"},
        "overrides": {"5": {"username": "PIDD85D", "password": "Present@1234.com"}}
    },
    "linux": {
        "default": {"username": "piddb58", "password": "External@1234"},
        "overrides": {"5": {"username": "piddb58", "password": "External@12345"}}
    }
}
```
**Modify to:** Change passwords, add bench-specific overrides.

### jira_config.json
```json
{
    "base_url": "https://mercedes-benz.atlassian.net",
    "user_email": "adarsh.priyadarshi@mercedes-benz.com",
    "api_token": "YOUR_JIRA_API_TOKEN",
    "project_key": "ADASDAI"
}
```
**Modify to:** Change Jira instance, rotate API token, change project.

### config.ini (per bench PC)
```ini
[server]
url = http://c623drd41380439:8000
timeout = 10

[bench]
bench_id = 1
pc_type = windows
```

---

## Database Schema

```sql
-- 10 rows (5 benches × 2 pc_types), always present
CREATE TABLE bench_status (
    bench_id INTEGER NOT NULL,
    pc_type TEXT NOT NULL CHECK(pc_type IN ('windows', 'linux')),
    status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'occupied')),
    short_id TEXT,
    purpose TEXT,
    access_method TEXT CHECK(access_method IN ('rdp', 'nomachine', 'physical', NULL)),
    start_time TEXT,
    PRIMARY KEY (bench_id, pc_type)
);

-- Grows over time, one row per session
CREATE TABLE usage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bench_id INTEGER NOT NULL,
    pc_type TEXT NOT NULL,
    short_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    access_method TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_min REAL
);
```

---

## Deployment

### Server Deployment (Linux: c623drd41380439)

**First time setup:**
```bash
cd ~/Desktop/Bench_Usage_Automation/server
chmod +x *.sh
./setup_server.sh
source venv/bin/activate
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
pip install -r requirements.txt
pip install httpx
```

**Start server:**
```bash
cd ~/Desktop/Bench_Usage_Automation/server
source venv/bin/activate
cd app
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

**Or use the script:**
```bash
./run_server.sh
```

**Stop server:**
```bash
pkill -f "uvicorn main:app"
```

**Verify:**
```bash
ps aux | grep uvicorn
curl --noproxy '*' http://localhost:8000/api/health
```

**IMPORTANT:** When copying server files, NEVER overwrite:
- `venv/` (packages installed)
- `app/bench_data.db` (live data)

---

### Client Deployment (per bench PC)

**Files needed per bench:**
- session_monitor.py
- login_gate.py
- startup_cleanup.py
- config.ini (bench-specific bench_id)
- MBRDI.png
- venv/ (with packages installed)

**Scheduled tasks (3 per bench):**
```cmd
schtasks /create /tn "BenchStartupCleanup" /tr "\"<path>\venv\Scripts\pythonw.exe\" \"<path>\startup_cleanup.py\"" /sc onstart /ru SYSTEM /rl highest /f
schtasks /create /tn "BenchSessionMonitor" /tr "\"<path>\venv\Scripts\pythonw.exe\" \"<path>\session_monitor.py\"" /sc onlogon /rl highest /f
schtasks /create /tn "BenchSessionMonitorWatchdog" /tr "\"<path>\venv\Scripts\pythonw.exe\" \"<path>\session_monitor.py\"" /sc minute /mo 5 /rl highest /f
```

**Quick deploy commands (Benches 1-4):**
```cmd
cd C:\Users\PIDDB58\Documents\Bench_Usage_Automation
taskkill /f /im pythonw.exe
del .login_gate.lock 2>nul
del .session_monitor.lock 2>nul
start "" venv\Scripts\pythonw.exe session_monitor.py
```

**Bench 5 (Pallava) uses different user:** `C:\Users\pidd85D\Documents\Bench_Usage_Automation`

**Chola special note:** onlogon task doesn't fire on Chola. Workaround: Startup folder .bat file.

---

## Bench Information

| Bench | Name | Architecture | Windows Hostname | Linux Hostname | User |
|-------|------|-------------|-----------------|----------------|------|
| 1 | Vijayanagara | ST3 | CGSCLXR85387250 | C623LRD90775115 | PIDDB58 |
| 2 | Maurya | ST35 | CGSCLXR88863425 | C623LRD89895681 | PIDDB58 |
| 3 | Chola | ST3 | CGSCLXR90775160 | C623LRD84052272 | PIDDB58 |
| 4 | Magadha | ST35 | CGSCLXR85739890 | C623LRD83422370 | PIDDB58 |
| 5 | Pallava | ST35 | CGSCLXR90775219 | C623LRD90042984 | PIDD85D |

---

## Feature Guide — What to Change

| Feature | Files to Modify |
|---------|----------------|
| Add/rename a bench | `server/config/benches.json`, `models.py` (bench_id range) |
| Add/remove users | `server/config/users.json` |
| Change login gate purposes | `client_windows/login_gate.py` (purposes list ~line 220) |
| Change dashboard refresh rate | `server/app/static/js/dashboard.js` (REFRESH_INTERVAL) |
| Change timer color thresholds | `server/app/static/js/dashboard.js` (updateTimers function) |
| Add new dashboard button | `dashboard.js` (renderBenchCard) + `dashboard.css` |
| Add new API endpoint | `routes/bench_routes.py` + `models.py` + `main.py` (if new file) |
| Add new page | `templates/new.html` + `main.py` (page route) + nav links in all templates |
| Change restart credentials | `server/config/credentials.json` |
| Change donut chart colors | `server/app/routes/jira_routes.py` (STATUS_COLORS dict) |
| Change bar chart color | `server/app/static/js/defect_board.js` (backgroundColor in chart) |
| Change Jira project/query | `server/app/routes/jira_routes.py` (SYSFUNC_LABELS, build_base_jql) |
| Change Jira API token | `server/config/jira_config.json` |
| Change defect board refresh rate | `server/app/static/js/defect_board.js` (AUTO_REFRESH_INTERVAL) |
| Modify Dr. Burn SW extraction | `drburn-7.1.6/src/drburn.py` (regex patterns) |
| Purple card for different purpose | `dashboard.js` (isFlashing condition) |

---

## Dr. Burn Integration — SW Version Extraction

**What it does:** After successful bench flashing with Dr. Burn tool, automatically updates the dashboard with new SW version and architecture.

**Log location:** `/root/.config/drburn/drburn-YYYY-MM-DD_HH-MM-SS-XXXXXX.log`

**Key log line:**
```
|14:51:09.064| INFO | Processing URL https://artifacts.swf.i.mercedes-benz.com/artifactory/adasndas/vint/2.8.9/R18.6.3/26_24/.../Base_st35-C4_dbg.../ddu/...tgz
```

**Extraction logic:**
- SW Version: regex `/R(\d+\.\d+\.\d+)/` → captures "R18.6.3"
- Architecture: regex `Base_(st\d+)` → captures "st35" → "ST35"

**Hostname mapping (Linux bench PCs):**
```python
_hostname_map = {
    "c623lrd90775115": 1,  # Vijayanagara
    "c623lrd89895681": 2,  # Maurya
    "c623lrd84052272": 3,  # Chola
    "c623lrd83422370": 4,  # Magadha
    "c623lrd90042984": 5,  # Pallava
}
```

**Flow:** Flash success → flush log → read log → extract SW + arch → detect bench by hostname → POST /api/update-bench-sw

**File to modify:** `drburn-7.1.6/src/drburn.py` (inside `if flash_success:` block)

---

## Debug Commands — Instant Solutions

### Server (Linux)
```bash
# Check server status
ps aux | grep uvicorn
curl --noproxy '*' http://localhost:8000/api/health

# View logs
tail -50 ~/Desktop/Bench_Usage_Automation/server/app/server.log

# Release stuck bench
curl --noproxy '*' -X POST http://localhost:8000/api/checkout -H "Content-Type: application/json" -d '{"bench_id": 3, "pc_type": "windows"}'

# View all bench status
curl --noproxy '*' http://localhost:8000/api/benches | python3 -m json.tool

# Database check
sqlite3 ~/Desktop/Bench_Usage_Automation/server/app/bench_data.db "SELECT * FROM bench_status;"
sqlite3 ~/Desktop/Bench_Usage_Automation/server/app/bench_data.db "SELECT * FROM usage_history ORDER BY id DESC LIMIT 10;"

# Release ALL benches (emergency)
sqlite3 ~/Desktop/Bench_Usage_Automation/server/app/bench_data.db "UPDATE bench_status SET status='available', short_id=NULL, purpose=NULL, access_method=NULL, start_time=NULL;"

# Test Jira API
curl --noproxy '*' http://localhost:8000/api/jira/overview
```

### Bench PC (Windows)
```cmd
:: Check if monitor is running
tasklist | findstr python

:: View session monitor log
type C:\Users\PIDDB58\Documents\Bench_Usage_Automation\session_monitor.log

:: Fix login gate not appearing
del .login_gate.lock 2>nul
del .session_monitor.lock 2>nul
start "" venv\Scripts\pythonw.exe session_monitor.py

:: Kill all and restart fresh
taskkill /f /im pythonw.exe
del .login_gate.lock 2>nul
del .session_monitor.lock 2>nul
start "" venv\Scripts\pythonw.exe session_monitor.py

:: Check scheduled tasks
schtasks /query /tn "BenchStartupCleanup"
schtasks /query /tn "BenchSessionMonitor"
schtasks /query /tn "BenchSessionMonitorWatchdog"

:: Run monitor visibly (to see errors)
venv\Scripts\python.exe session_monitor.py
```

---

## Known Issues & Workarounds

| Issue | Cause | Workaround |
|-------|-------|------------|
| Win+L on physical bench causes false re-occupy | Spurious REMOTE_CONNECT after SESSION_LOCK | 15s cooldown + manual Release button |
| Chola onlogon task never fires | Unknown Windows Task Scheduler issue | Startup folder .bat file |
| Jira defect board not loading on Linux server | ALL_PROXY env var set to socks:// which httpx can't handle | Unset ALL_PROXY before starting server, or use trust_env=False |
| Dashboard stale in background tab | Browser throttles setInterval | Page Visibility API + 10min auto-reload |
| Corporate proxy blocking requests | Env vars route traffic through auth-required proxy | proxies={"http": None, "https": None} for internal calls |

---

## Security Considerations

**Implemented:**
- Input validation (Pydantic: regex, length, type checks)
- XSS prevention (HTML tags stripped, escapeHtml() in frontend)
- CORS middleware (restricts origins)
- Generic error messages (no system info leaked)
- Credentials in separate config files

**Not implemented (internal tool trade-offs):**
- No authentication (internal network only)
- No HTTPS (corporate network)
- Plaintext credentials in JSON
- No rate limiting
- No API keys

---

## Dependencies

### Server (requirements.txt)
```
fastapi==0.115.0
uvicorn==0.30.0
jinja2==3.1.4
pydantic==2.9.0
requests>=2.32.3
httpx>=0.27.0
```

### Client (requirements.txt)
```
requests>=2.32.3
pywin32>=306
Pillow>=10.0.0
```

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Uvicorn, SQLite (WAL mode) |
| Frontend | HTML5, CSS3 (dark theme), Vanilla JavaScript, Chart.js |
| Client Automation | Python, pywin32 (WTS API), Tkinter, Pillow |
| External API | Jira Cloud REST API v3 (via httpx) |
| Infrastructure | Linux Ubuntu (server), Windows 11 (benches), Task Scheduler |
| Remote Operations | net rpc (Windows restart), sshpass+SSH (Linux restart) |
