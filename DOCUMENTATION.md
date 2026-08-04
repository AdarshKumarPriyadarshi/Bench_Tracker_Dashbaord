# System Function Bench Tracker — Operations & Maintenance Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Access Points](#access-points)
3. [Server Setup — Step by Step](#server-setup)
4. [Client Setup — Step by Step](#client-setup)
5. [Day-to-Day Operations](#daily-ops)
6. [Feature Workflows](#feature-workflows)
7. [Jira Defect Board](#jira-defect-board)
8. [Dr. Burn SW Version Auto-Update](#drburn)
9. [Modifying Features](#modifying-features)
10. [Adding a New Bench](#adding-bench)
11. [Adding a New User](#adding-user)
12. [Updating Files on Server](#updating-server)
13. [Updating Files on Bench PCs](#updating-clients)
14. [Maintenance Procedures](#maintenance)
15. [Troubleshooting Guide](#troubleshooting)
16. [Emergency Procedures](#emergency)
17. [Known Limitations](#known-limitations)
18. [Handover Checklist](#handover)

---

## 1. Introduction <a name="introduction"></a>

This system automates bench usage tracking for 5 shared open-loop test benches. When a user connects via RDP, a login gate forces identification. When they disconnect, the bench is automatically released. The dashboard shows real-time status to all team members.

**Components:**
- **Server** — FastAPI on Linux, serves dashboard + APIs
- **Client** — Python scripts on each bench PC, detect session events
- **Dashboard** — Browser-based UI, polls server every 5 seconds
- **Defect Board** — Integrated Jira defect tracking page

---

## 2. Access Points <a name="access-points"></a>

| Resource | URL / Location |
|----------|---------------|
| Dashboard | http://c623drd41380439:8000 |
| History | http://c623drd41380439:8000/history |
| Statistics | http://c623drd41380439:8000/statistics |
| Defect Board | http://c623drd41380439:8000/defect-board |
| Bench Detail | http://c623drd41380439:8000/bench/{1-5} |
| Swagger API Docs | http://c623drd41380439:8000/docs |
| Server PC | c623drd41380439 (SSH: piddb58 / External@1234) |
| Server files | ~/Desktop/Bench_Usage_Automation/server/ |
| Bench PC files | C:\Users\PIDDB58\Documents\Bench_Usage_Automation\ |
| Bench 5 files | C:\Users\pidd85D\Documents\Bench_Usage_Automation\ |

---

## 3. Server Setup — Step by Step <a name="server-setup"></a>

### Prerequisites
- Ubuntu Linux with Python 3.11+
- Network connectivity to bench PCs (internal)
- Network connectivity to atlassian.net (for Jira, may need proxy)

### First-Time Installation

```bash
# 1. Create directory
mkdir -p ~/Desktop/Bench_Usage_Automation/server
cd ~/Desktop/Bench_Usage_Automation/server

# 2. Copy all server files from source

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Clear proxy (corporate network issue)
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY

# 5. Install dependencies
pip install -r requirements.txt
pip install httpx

# 6. Make scripts executable
chmod +x *.sh

# 7. Start server
./run_server.sh
# OR manually:
cd app
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Verify Installation
```bash
curl --noproxy '*' http://localhost:8000/api/health
# Expected: {"status":"ok","service":"bench-usage-automation"}

curl --noproxy '*' http://localhost:8000/api/benches | python3 -m json.tool
# Expected: Array of 10 bench status objects
```

---

## 4. Client Setup — Step by Step <a name="client-setup"></a>

### Prerequisites per bench
- Windows 11
- Python 3.11 installed
- Network access to server (http://c623drd41380439:8000)

### First-Time Installation

```cmd
:: 1. Create directory
mkdir C:\Users\PIDDB58\Documents\Bench_Usage_Automation
cd C:\Users\PIDDB58\Documents\Bench_Usage_Automation

:: 2. Copy files: session_monitor.py, login_gate.py, startup_cleanup.py, MBRDI.png

:: 3. Create virtual environment
python -m venv venv

:: 4. Install dependencies
venv\Scripts\pip install requests pywin32 Pillow --proxy ""

:: 5. Create config.ini (change bench_id per bench!)
(
echo [server]
echo url = http://c623drd41380439:8000
echo timeout = 10
echo.
echo [bench]
echo bench_id = 1
echo pc_type = windows
) > config.ini

:: 6. Create scheduled tasks
schtasks /create /tn "BenchStartupCleanup" /tr "\"C:\Users\PIDDB58\Documents\Bench_Usage_Automation\venv\Scripts\pythonw.exe\" \"C:\Users\PIDDB58\Documents\Bench_Usage_Automation\startup_cleanup.py\"" /sc onstart /ru SYSTEM /rl highest /f
schtasks /create /tn "BenchSessionMonitor" /tr "\"C:\Users\PIDDB58\Documents\Bench_Usage_Automation\venv\Scripts\pythonw.exe\" \"C:\Users\PIDDB58\Documents\Bench_Usage_Automation\session_monitor.py\"" /sc onlogon /rl highest /f
schtasks /create /tn "BenchSessionMonitorWatchdog" /tr "\"C:\Users\PIDDB58\Documents\Bench_Usage_Automation\venv\Scripts\pythonw.exe\" \"C:\Users\PIDDB58\Documents\Bench_Usage_Automation\session_monitor.py\"" /sc minute /mo 5 /rl highest /f

:: 7. Start monitor
start "" venv\Scripts\pythonw.exe session_monitor.py
```

### Bench ID Assignment
| Bench | bench_id | Directory User |
|-------|----------|----------------|
| Vijayanagara | 1 | PIDDB58 |
| Maurya | 2 | PIDDB58 |
| Chola | 3 | PIDDB58 |
| Magadha | 4 | PIDDB58 |
| Pallava | 5 | pidd85D |

### Verify Client Installation
```cmd
:: Check processes running
tasklist | findstr python

:: Check scheduled tasks exist
schtasks /query /tn "BenchStartupCleanup"
schtasks /query /tn "BenchSessionMonitor"
schtasks /query /tn "BenchSessionMonitorWatchdog"

:: Check config
type config.ini

:: Check log
type session_monitor.log
```

---

## 5. Day-to-Day Operations <a name="daily-ops"></a>

### Normal Operation (no action needed)
The system runs autonomously. Users connect via RDP → login gate appears → they check in → they disconnect → bench releases automatically.

### If Server Reboots
The server does NOT auto-start uvicorn. You must SSH in and start it:
```bash
ssh piddb58@c623drd41380439
cd ~/Desktop/Bench_Usage_Automation/server
./run_server.sh
```

### If Bench PC Reboots
`BenchStartupCleanup` (SYSTEM, onstart) automatically:
1. Clears stale lock files
2. Sends checkout to release bench on dashboard

Then when user logs in:
`BenchSessionMonitor` (onlogon) automatically starts the session monitor.

### Checking Dashboard Health
Open http://c623drd41380439:8000 — if it loads, server is running.
If "Server Offline" banner appears, SSH to server and restart.

---

## 6. Feature Workflows <a name="feature-workflows"></a>

### How Check-in Works
1. User connects RDP → Windows fires `WTS_REMOTE_CONNECT` event
2. `session_monitor.py` receives event via message pump
3. Checks: debounce OK? gate not running? → launches `login_gate.py`
4. Fullscreen gate appears → user enters Short ID + Purpose
5. Background thread sends `POST /api/checkin` to server
6. Server validates → updates both Windows + Linux status
7. Gate closes → user has desktop → dashboard shows occupied within 5s

### How Check-out Works
1. User disconnects RDP → Windows fires `WTS_REMOTE_DISCONNECT`
2. `session_monitor.py` sends `POST /api/checkout` immediately
3. Server moves record to usage_history, clears bench_status
4. Dashboard shows available within 5s
5. Browser notification sent to all open dashboards

### How Restart Works
1. User clicks Restart on dashboard → selects WINDOWS or LINUX
2. Frontend sends `POST /api/restart-bench`
3. Server verifies bench not occupied
4. Windows: `net rpc shutdown -r -f -I <hostname> -U user%pass`
5. Linux: `sshpass -p <pass> ssh user@host "echo pass | sudo -S reboot"`
6. Bench reboots → `startup_cleanup.py` releases it on dashboard

### How Release Request Works
1. User clicks "Request" on an occupied bench card
2. Modal opens: select requester + purpose
3. Constructs Microsoft Teams deep link with pre-typed message
4. Opens Teams → user sends message to occupant

### How Manual Release Works (Physical Access)
1. If bench shows `access_method: physical`, a "Release" button appears
2. User clicks → confirm dialog → `POST /api/checkout`
3. Bench released immediately on dashboard

---

## 7. Jira Defect Board <a name="jira-defect-board"></a>

### Overview
The Defect Board page fetches bug data from Jira Cloud and displays it with the same dark-themed UI as the bench dashboard.

### How It Works
1. Frontend loads → calls 3 API endpoints in parallel
2. Server reads `jira_config.json` for credentials
3. `JiraClient` calls Jira REST API (`/rest/api/3/search/jql`)
4. Results cached for 180 seconds
5. Frontend renders: stats cards, donut chart, bar chart, sysfunc table, defect list

### Jira Configuration
File: `server/config/jira_config.json`
```json
{
    "base_url": "https://mercedes-benz.atlassian.net",
    "user_email": "your.email@mercedes-benz.com",
    "api_token": "YOUR_TOKEN",
    "project_key": "ADASDAI"
}
```

### Generating Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it (e.g., "Bench Tracker")
4. Copy token → paste in `jira_config.json`

### Jira Query Logic
The system queries bugs with these labels:
- Must have: `SYS4_Bench_Test`
- Must have one of: Dimming, PRD, GTS, POM, PDD, PSSDS, DLCS, DLLR, SSPN, SEM_ROV, ODF, Presafe, Visualisation, CCHP, PTS_Op_Mode, SVS_Op_Mode, ALSA, PWD, AR, VRP, VBPS

Optional filters (via dropdown):
- Release: R16, R17, R18, R19, R21 (added as `AND labels = "R18"`)
- Candidate: MF4, MF5
- Safety: FUSA, NON_FUSA

### Defect Board Features
- Stats cards: Total Bugs, Ongoing (blue), Closed (green)
- Donut chart: Ongoing status distribution
- Bar chart: Module wise distribution (orange vertical bars)
- Category tabs: Parking, Miscellaneous, Driving Function, ODF, ROV
- SysFunc table: Acronym, Name, Tester, Ongoing, Closed, Total
- Defect list: Key (links to Jira), Status, Priority, Summary, Reporter, Assignee, Comment
- Pagination: 20 items per page
- Auto-refresh: every 120 seconds
- Live indicator: green dot + "Updated: Xs ago"

### Known Issue: Proxy on Linux Server
The Linux server may have `ALL_PROXY=socks://...` environment variable that breaks httpx. Solutions:
1. Unset before starting: `unset ALL_PROXY all_proxy`
2. Add `trust_env=False` to httpx client in jira_routes.py
3. Run defect board from Windows laptop (where Jira is reachable directly)

---

## 8. Dr. Burn SW Version Auto-Update <a name="drburn"></a>

### What It Does
After a successful ECU flash with Dr. Burn tool, the dashboard automatically updates the bench's SW version and architecture.

### How It Works
1. Dr. Burn flashes ECU successfully
2. Log handlers flushed to disk
3. Script reads the session log file at `/root/.config/drburn/`
4. Searches for "Processing URL" lines containing "artifacts.swf"
5. Extracts SW version via regex: `/R(\d+\.\d+\.\d+)/` → "R18.6.3"
6. Extracts architecture via regex: `Base_(st\d+)` → "ST35"
7. Detects bench by hostname mapping
8. Sends `POST /api/update-bench-sw` to dashboard

### File to Modify
`drburn-7.1.6/src/drburn.py` — inside the `if flash_success:` block

### Testing Without Flashing
Copy `debug_drburn_update.py` to a bench Linux PC and run:
```bash
sudo python3 debug_drburn_update.py
```
This reads the latest log and sends the extracted data to the dashboard.

### Viewing Logs
```bash
sudo grep "Processing URL" /root/.config/drburn/drburn-*.log | tail -5
```

---

## 9. Modifying Features <a name="modifying-features"></a>

### Change Login Gate Purposes
**File:** `client_windows/login_gate.py`
**Location:** ~line 220, `purposes` list
```python
purposes = [
    "Automation Execution", "Automation Integration",
    "Bench Debugging (HW)", "Software Flashing",
    ...
]
```
**Deploy:** Copy to all bench PCs, restart monitor.

### Change Dashboard Refresh Rate
**File:** `server/app/static/js/dashboard.js`
**Line 1:** `const REFRESH_INTERVAL = 5000;`
**Deploy:** Copy to server, hard refresh browser.

### Change Timer Color Thresholds
**File:** `server/app/static/js/dashboard.js`
**Function:** `updateTimers()`
```javascript
if (mins > 60) el.style.color = "#ff1744";      // red
else if (mins > 45) el.style.color = "#ff6e40";  // orange-red
else if (mins > 30) el.style.color = "#ffa726";  // orange
else if (mins > 15) el.style.color = "#ffd740";  // yellow
else el.style.color = "#ffffff";                  // white
```

### Change Jira Donut Chart Colors
**File:** `server/app/routes/jira_routes.py`
**Dict:** `STATUS_COLORS`
```python
STATUS_COLORS = {
    "Open": "#eab308",      # yellow
    "Done": "#22c55e",      # green
    "Testing": "#06b6d4",   # cyan
    "To Do": "#f97316",     # orange
    "Rejected": "#dc2626",  # red
    ...
}
```

### Change Jira Bar Chart Color
**File:** `server/app/static/js/defect_board.js`
**In `renderModuleBarChart()`:** `backgroundColor: "#f97316"`

### Enable Purple Flashing Card for Different Purpose
**File:** `server/app/static/js/dashboard.js`
**In `renderBenchCard()`:**
```javascript
const isFlashing = isOccupied && data.purpose && data.purpose.toLowerCase().includes("flashing");
```
Change `"flashing"` to your keyword.

### Add New Defect Board Filter Option
**File:** `server/app/templates/defect_board.html`
Add `<option>` to the relevant `<select>` dropdown.

### Change Defect Board Auto-Refresh Interval
**File:** `server/app/static/js/defect_board.js`
**Line:** `const AUTO_REFRESH_INTERVAL = 120000;`

---

## 10. Adding a New Bench <a name="adding-bench"></a>

1. **Update benches.json:**
```json
{
    "bench_id": 6,
    "name": "NewBench",
    "architecture": "ST3",
    "sw_version": "R18.6.3",
    "windows_hostname": "HOSTNAME",
    "windows_ip": "x.x.x.x",
    "linux_hostname": "HOSTNAME",
    "linux_ip": "x.x.x.x"
}
```

2. **Update models.py** — change `le=5` to `le=6`:
```python
bench_id: int = Field(ge=1, le=6)
```

3. **Update database.py** — change `range(1, 6)` to `range(1, 7)` in init_db()

4. **Deploy client** on the new bench PC (session_monitor + login_gate + startup_cleanup)

5. **Create config.ini** with `bench_id = 6`

6. **Restart server** to pick up new bench

---

## 11. Adding a New User <a name="adding-user"></a>

**File:** `server/config/users.json`

Add entry:
```json
"NEWUSER": {
    "name": "Full Name",
    "email": "full.name@mercedes-benz.com"
}
```

No server restart needed — `users.json` is reloaded on every `/api/benches` call.

---

## 12. Updating Files on Server <a name="updating-server"></a>

### Via WinSCP
1. Connect to `c623drd41380439` as `piddb58`
2. Navigate to `~/Desktop/Bench_Usage_Automation/server/`
3. Upload changed files (NEVER overwrite `venv/` or `bench_data.db`)
4. SSH in and restart:
```bash
pkill -f "uvicorn main:app"
cd ~/Desktop/Bench_Usage_Automation/server
./run_server.sh
```

### Via SCP (command line)
```bash
scp file.py piddb58@c623drd41380439:~/Desktop/Bench_Usage_Automation/server/app/routes/
```

### Files That Need Server Restart
- `main.py`
- `database.py`
- `models.py`
- Any file in `routes/`

### Files That DON'T Need Restart (just browser refresh)
- `templates/*.html`
- `static/css/*.css`
- `static/js/*.js`
- `config/*.json`

---

## 13. Updating Files on Bench PCs <a name="updating-clients"></a>

### Connect via RDP
Each bench has a shared account. Connect, then:

```cmd
cd C:\Users\PIDDB58\Documents\Bench_Usage_Automation

:: Stop everything
taskkill /f /im pythonw.exe

:: Delete lock files
del .session_monitor.lock 2>nul
del .login_gate.lock 2>nul

:: Copy updated files (session_monitor.py, login_gate.py, etc.)

:: Restart
start "" venv\Scripts\pythonw.exe session_monitor.py
```

### Verify After Update
```cmd
:: Check it's running
tasklist | findstr python

:: Check log shows new startup
type session_monitor.log | findstr "Session monitor started"
```

---

## 14. Maintenance Procedures <a name="maintenance"></a>

### Weekly
- Check dashboard loads: http://c623drd41380439:8000
- Verify all 5 benches show correct status
- Check server log for errors: `tail -100 server.log`

### Monthly
- Review `usage_history` size: `sqlite3 bench_data.db "SELECT COUNT(*) FROM usage_history;"`
- Check disk space on server: `df -h`
- Verify scheduled tasks on all benches: `schtasks /query /tn "BenchSessionMonitor"`
- Rotate Jira API token if needed

### If Server Disk Gets Full
```bash
# Check what's using space
du -sh ~/Desktop/Bench_Usage_Automation/server/app/*

# If bench_data.db is huge (>500MB), archive old history:
sqlite3 bench_data.db "DELETE FROM usage_history WHERE start_time < '2026-01-01';"
sqlite3 bench_data.db "VACUUM;"
```

### If Server Log Gets Large
```bash
# Truncate (don't delete — uvicorn holds file handle)
> ~/Desktop/Bench_Usage_Automation/server/app/server.log
```

---

## 15. Troubleshooting Guide <a name="troubleshooting"></a>

### Login gate not appearing
```cmd
cd C:\Users\PIDDB58\Documents\Bench_Usage_Automation
del .login_gate.lock 2>nul
del .session_monitor.lock 2>nul
start "" venv\Scripts\pythonw.exe session_monitor.py
```

### Bench stuck as "Occupied" on dashboard
```bash
# From server:
curl --noproxy '*' -X POST http://localhost:8000/api/checkout -H "Content-Type: application/json" -d '{"bench_id": X, "pc_type": "windows"}'
```

### Dashboard shows "Server Offline"
```bash
# SSH to server, check if running:
ps aux | grep uvicorn
# If nothing → restart:
cd ~/Desktop/Bench_Usage_Automation/server && ./run_server.sh
```

### Multiple login gates appearing
```cmd
taskkill /f /im pythonw.exe
del .session_monitor.lock 2>nul
del .login_gate.lock 2>nul
start "" venv\Scripts\pythonw.exe session_monitor.py
```

### Session monitor crashes repeatedly
```cmd
:: Run visibly to see the error:
venv\Scripts\python.exe session_monitor.py
```
Common causes: `requests` not installed, `pywin32` missing, wrong `config.ini`.

### Restart button says "Restart failed"
```bash
# Test from server manually:
net rpc shutdown -r -f -I CGSCLXR85387250 -U "PIDDB58%External@12345"
```
If it fails: check hostname reachable (`ping HOSTNAME`), check credentials.

### Defect board not loading (Internal Server Error)
```bash
# Check server log for specific error:
tail -20 ~/Desktop/Bench_Usage_Automation/server/app/server.log
```
Common causes:
- `ALL_PROXY` env var breaking httpx → unset it or add `trust_env=False`
- Jira API token expired → regenerate and update `jira_config.json`
- Network can't reach atlassian.net → run from Windows PC instead

### Statistics shows wrong numbers
- Ensure `history_routes.py` filters to `pc_type='windows'` only
- Check limit is high enough (should be 2000 for 90-day range)

---

## 16. Emergency Procedures <a name="emergency"></a>

### Release ALL Benches Immediately
```bash
sqlite3 ~/Desktop/Bench_Usage_Automation/server/app/bench_data.db "UPDATE bench_status SET status='available', short_id=NULL, purpose=NULL, access_method=NULL, start_time=NULL;"
```

### Server Completely Down — Bench Clients Keep Working
If server is unreachable:
- Login gate shows "Server offline — logged locally"
- Check-in saved to `local_checkins.json` on the bench PC
- User can still proceed (gate closes after attempt)
- When server comes back, dashboard won't show the local sessions (they're lost)

### Database Corrupted
```bash
# Stop server
pkill -f "uvicorn main:app"

# Delete database (will lose all history!)
rm ~/Desktop/Bench_Usage_Automation/server/app/bench_data.db

# Restart — init_db() will create fresh tables
./run_server.sh
```

### Kill Everything on a Bench PC
```cmd
taskkill /f /im pythonw.exe
taskkill /f /im python.exe
del C:\Users\PIDDB58\Documents\Bench_Usage_Automation\.session_monitor.lock 2>nul
del C:\Users\PIDDB58\Documents\Bench_Usage_Automation\.login_gate.lock 2>nul
```

---

## 17. Known Limitations <a name="known-limitations"></a>

1. **No authentication** — anyone on the network can access the dashboard and APIs
2. **No HTTPS** — all traffic is plaintext (acceptable for internal network)
3. **Polling-based** — 5-second delay, not true real-time (WebSockets would fix this)
4. **Single server** — no redundancy, if Linux PC dies dashboard is offline
5. **Win+L on physical bench** — spurious REMOTE_CONNECT events cause false re-occupy (workaround: 15s cooldown + manual Release button)
6. **Chola onlogon issue** — Task Scheduler onlogon trigger doesn't fire (workaround: Startup folder .bat)
7. **Jira API token expires** — needs manual rotation
8. **No server auto-start** — after server reboot, someone must SSH in and start uvicorn
9. **Local check-ins lost** — if server is down during check-in, the session is logged locally but never synced back

---

## 18. Handover Checklist <a name="handover"></a>

### Credentials to Share
- [ ] Server SSH: `piddb58@c623drd41380439` / `External@1234`
- [ ] Bench PCs (1-4): `PIDDB58` / `External@12345`
- [ ] Bench 5 (Pallava): `PIDD85D` / `Present@1234.com`
- [ ] Linux bench PCs: `piddb58` / `External@1234`
- [ ] Jira API token location: `server/config/jira_config.json`
- [ ] Restart credentials: `server/config/credentials.json`

### Access to Verify
- [ ] Can SSH to server
- [ ] Can open dashboard in browser
- [ ] Can RDP to at least one bench PC
- [ ] Can see session_monitor running on bench
- [ ] Can see login gate appear on RDP connect
- [ ] Can see checkout happen on RDP disconnect

### Documents to Read
- [ ] This file (DOCUMENTATION.md)
- [ ] ARCHITECTURE.md (technical structure)
- [ ] server/API_DOCUMENTATION.md (API reference)
- [ ] server/WORKFLOW.md (flow diagrams)

### Common Tasks to Practice
- [ ] Restart server after reboot
- [ ] Release a stuck bench from server
- [ ] Deploy updated file to a bench PC
- [ ] Add a new user to users.json
- [ ] Check server logs for errors
- [ ] Rotate Jira API token
- [ ] Run session_monitor visibly for debugging

### Source Code Location
- Git repository (to be pushed)
- Local: `C:\Users\ADPRIYA\Desktop\Bench_Info_Automation\`
- Server: `~/Desktop/Bench_Usage_Automation/server/`
- Bench PCs: `C:\Users\PIDDB58\Documents\Bench_Usage_Automation\`
