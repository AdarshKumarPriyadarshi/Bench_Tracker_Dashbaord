# System Function Bench Tracker — API & Integration Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [FastAPI Application Setup](#fastapi-application-setup)
4. [Database Layer](#database-layer)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Pydantic Models (Validation)](#pydantic-models)
7. [Configuration Files](#configuration-files)
8. [Frontend Integration](#frontend-integration)
9. [How to Add a New Tool/Endpoint](#how-to-add-a-new-tool)
10. [Integration Examples](#integration-examples)
11. [Deployment & Server Management](#deployment)
12. [Troubleshooting](#troubleshooting)

---

## 1. Architecture Overview <a name="architecture-overview"></a>

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NETWORK (VPN/Corporate)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐          ┌──────────────────────────────┐         │
│   │  Bench PC 1  │──RDP──►  │                              │         │
│   │  (Windows)   │          │     FastAPI Server            │         │
│   │  session_    │──POST──► │     (c623drd41380439:8000)    │         │
│   │  monitor.py  │          │                              │         │
│   └──────────────┘          │  ┌─────────┐ ┌───────────┐  │         │
│                              │  │ Routes  │ │ Database  │  │         │
│   ┌──────────────┐          │  │         │ │ (SQLite)  │  │         │
│   │  Bench PC 2  │──POST──► │  │ bench_  │ │           │  │         │
│   │  Bench PC 3  │──POST──► │  │ routes  │ │ bench_    │  │         │
│   │  Bench PC 4  │──POST──► │  │         │ │ data.db   │  │         │
│   │  Bench PC 5  │──POST──► │  │ history_│ │           │  │         │
│   └──────────────┘          │  │ routes  │ └───────────┘  │         │
│                              │  └─────────┘                │         │
│   ┌──────────────┐          │                              │         │
│   │  Dashboard   │◄──GET──  │  ┌─────────┐ ┌───────────┐  │         │
│   │  (Browser)   │          │  │Templates│ │  Static   │  │         │
│   │  Polls /api/ │          │  │ (HTML)  │ │ (CSS/JS)  │  │         │
│   │  every 5s    │          │  └─────────┘ └───────────┘  │         │
│   └──────────────┘          │                              │         │
│                              └──────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow:
1. **Check-in:** Bench PC connects → Session monitor detects → `POST /api/checkin` → DB stores status
2. **Check-out:** Bench PC disconnects → Session monitor detects → `POST /api/checkout` → DB updates
3. **Dashboard:** Browser polls `GET /api/benches` every 5s → Renders real-time status
4. **Actions:** User clicks Restart/Request → `POST /api/restart-bench` or `/api/request-release` → Server executes

---

## 2. Project Structure <a name="project-structure"></a>

```
server/
├── app/
│   ├── main.py                  # FastAPI app initialization, middleware, page routes
│   ├── database.py              # SQLite database operations (CRUD)
│   ├── models.py                # Pydantic request/response models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── bench_routes.py      # /api/checkin, /api/checkout, /api/benches, /api/restart-bench
│   │   ├── history_routes.py    # /api/history, /api/statistics
│   │   └── jira_routes.py       # /api/jira/* — Jira Defect Board APIs
│   ├── templates/
│   │   ├── dashboard.html       # Main dashboard page
│   │   ├── history.html         # Usage history page
│   │   ├── statistics.html      # Statistics/analytics page
│   │   ├── bench_detail.html    # Individual bench detail page
│   │   └── defect_board.html    # Jira Defect Board page
│   ├── static/
│   │   ├── css/
│   │   │   ├── dashboard.css    # Main stylesheet (all pages)
│   │   │   ├── bench_detail.css # Bench detail specific styles
│   │   │   ├── statistics.css   # Statistics page specific styles
│   │   │   └── defect_board.css # Defect Board specific styles
│   │   ├── js/
│   │   │   ├── dashboard.js     # Dashboard + History page logic
│   │   │   ├── statistics.js    # Statistics page charts
│   │   │   ├── defect_board.js  # Defect Board logic (Jira integration)
│   │   │   ├── chart.umd.min.js # Chart.js library (local)
│   │   │   └── chartjs-adapter-date-fns.bundle.min.js
│   │   └── MBRDI.png            # Logo
│   └── bench_data.db            # SQLite database file
├── config/
│   ├── benches.json             # Bench metadata (hostname, IP, architecture, SW version)
│   ├── users.json               # User directory (short_id, name, email)
│   ├── credentials.json         # Remote restart credentials
│   └── jira_config.json         # Jira API credentials (base_url, email, token)
├── requirements.txt             # Python dependencies
├── setup_server.sh              # Server setup script
└── run_server.sh                # Server start script
```

---

## 3. FastAPI Application Setup <a name="fastapi-application-setup"></a>

### main.py — Entry Point

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bench Usage Automation", version="1.0.0")

# CORS — restrict to known origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://c623drd41380439:8000", "http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# HTML templates
templates = Jinja2Templates(directory="templates")

# Register route modules
app.include_router(bench_router)   # /api/checkin, /api/checkout, etc.
app.include_router(history_router) # /api/history, /api/statistics
app.include_router(jira_router)    # /api/jira/* (defect board)

# Initialize database on startup
@app.on_event("startup")
def startup():
    db.init_db()
```

### How Uvicorn runs it:
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```
- `main` = filename (main.py)
- `app` = FastAPI instance variable name
- `--host 0.0.0.0` = listen on all network interfaces
- `--port 8000` = port number

---

## 4. Database Layer <a name="database-layer"></a>

### Database: SQLite (`bench_data.db`)

#### Tables:

**bench_status** — Current state of each bench
```sql
CREATE TABLE bench_status (
    id INTEGER PRIMARY KEY,
    bench_id INTEGER,
    pc_type TEXT,          -- 'windows' or 'linux'
    status TEXT,           -- 'available' or 'occupied'
    short_id TEXT,         -- User's short ID (e.g., 'ADPRIYA')
    purpose TEXT,          -- Why they're using it
    access_method TEXT,    -- 'rdp', 'physical', 'nomachine'
    start_time TEXT        -- ISO timestamp of check-in
);
```

**usage_history** — Historical record of all sessions
```sql
CREATE TABLE usage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bench_id INTEGER,
    pc_type TEXT,
    short_id TEXT,
    purpose TEXT,
    access_method TEXT,
    start_time TEXT,
    end_time TEXT,
    duration_min REAL
);
```

#### Database Functions (database.py):

| Function | Description |
|---|---|
| `init_db()` | Creates tables if not exist, seeds initial bench_status rows |
| `get_all_benches()` | Returns current status of all benches |
| `checkin(bench_id, pc_type, short_id, purpose, access_method)` | Sets bench to occupied |
| `checkout(bench_id, pc_type)` | Sets bench to available, moves to history |
| `get_history(bench_id, short_id, limit, date_from, date_to)` | Queries usage_history |

---

## 5. API Endpoints Reference <a name="api-endpoints-reference"></a>

### Page Routes (HTML)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard page |
| `GET` | `/history` | Usage history page |
| `GET` | `/statistics` | Statistics/analytics page |
| `GET` | `/bench/{bench_id}` | Individual bench detail page |
| `GET` | `/defect-board` | Jira Defect Board page |

### API Routes (JSON)

#### GET /api/benches
Returns current status of all benches.

**Response:**
```json
[
    {
        "bench_id": 1,
        "pc_type": "windows",
        "status": "occupied",
        "short_id": "ADPRIYA",
        "purpose": "Software Debug",
        "access_method": "rdp",
        "start_time": "2026-06-23T10:30:00",
        "bench_name": "Vijayanagara",
        "architecture": "ST3",
        "sw_version": "R18.6.3",
        "win_hostname": "CGSCLXR85387250",
        "lin_hostname": "C623LRD90775115",
        "user_email": "adarsh.priyadarshi@mercedes-benz.com",
        "user_name": "Adarsh Priyadarshi"
    },
    ...
]
```

#### POST /api/checkin
Check in to a bench.

**Request Body:**
```json
{
    "bench_id": 1,
    "pc_type": "windows",
    "short_id": "ADPRIYA",
    "purpose": "Software Debug",
    "access_method": "rdp"
}
```

**Validation:**
- `bench_id`: integer, 1-5
- `pc_type`: "windows" or "linux"
- `short_id`: alphanumeric + underscore, 1-50 chars
- `purpose`: 1-200 chars, HTML stripped
- `access_method`: "rdp", "nomachine", or "physical"

**Response:**
```json
{
    "status": "ok",
    "message": "Checked in to Bench 1 (both PCs)",
    "start_time": "2026-06-23T10:30:00"
}
```

#### POST /api/checkout
Release a bench.

**Request Body:**
```json
{
    "bench_id": 1,
    "pc_type": "windows"
}
```

**Response:**
```json
{
    "status": "ok",
    "message": "Checked out from Bench 1 (both PCs)",
    "duration_min": 45.2
}
```

#### GET /api/history
Get usage history records.

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `bench_id` | int | null | Filter by bench (1-5) |
| `short_id` | string | null | Filter by user |
| `limit` | int | 100 | Max records (max 500) |
| `date_from` | string | null | ISO date string |
| `date_to` | string | null | ISO date string |

**Response:** Array of history records (filtered to windows only, deduplicated)

#### GET /api/statistics
Get aggregated statistics.

**Query Parameters:** Same as /api/history

**Response:**
```json
{
    "summary": {
        "total_sessions": 42,
        "avg_duration_min": 35.5,
        "total_duration_min": 1491.0,
        "most_used_bench": 2,
        "busiest_day": "2026-06-17",
        "top_user": "MONAYAZ"
    },
    "records": [...]
}
```

#### GET /api/users
Get all registered users.

**Response:**
```json
[
    {"short_id": "ADPRIYA", "name": "Adarsh Priyadarshi"},
    {"short_id": "MONAYAZ", "name": "Mohammed Nayaz"},
    ...
]
```

#### POST /api/request-release
Request bench release (sends Teams message).

**Request Body:**
```json
{
    "bench_id": 2,
    "requester_id": "ADPRIYA",
    "purpose": "Software Debug"
}
```

#### POST /api/restart-bench
Remote restart a bench PC.

**Request Body:**
```json
{
    "bench_id": 1,
    "pc_type": "windows"
}
```

**Logic:**
- Windows: `net rpc shutdown -r -f -I <hostname> -U <user>%<pass>`
- Linux: `sshpass -p <pass> ssh <user>@<hostname> "echo '<pass>' | sudo -S reboot"`

#### GET /api/health
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "bench-usage-automation"}
```

#### POST /api/update-bench-sw
Update bench SW version (called by Dr. Burn after flash).

**Request Body:**
```json
{
    "bench_id": 1,
    "sw_version": "R18.6.3",
    "architecture": "ST35"
}
```

**Response:**
```json
{"status": "ok", "message": "Bench 1 updated to R18.6.3 (ST35)"}
```

---

### Jira Defect Board API Routes

#### GET /api/jira/overview
Get defect summary (total, ongoing, closed, aging, priorities, status distribution).

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `project_key` | string | "ADASDAI" | Jira project key |
| `release` | string | null | Release version filter (R16, R17, R18, R19, R21) |
| `release_candidate` | string | null | Release candidate filter (MF4, MF5) |
| `safety_type` | string | null | Safety type filter (FUSA, NON_FUSA) |

**Response:**
```json
{
    "total": 42,
    "ongoing_count": 18,
    "closed_count": 24,
    "aging": [
        {"label": "0-7d", "count": 0, "color": "#22c55e"},
        {"label": "7-14d", "count": 0, "color": "#eab308"},
        {"label": "14-30d", "count": 0, "color": "#f97316"},
        {"label": "30d+", "count": 42, "color": "#dc2626"}
    ],
    "priorities": [
        {"priority": "High", "count": 7, "color": "#f97316"},
        {"priority": "Medium", "count": 32, "color": "#eab308"}
    ],
    "status_distribution": [
        {"status": "Open", "count": 5, "color": "#eab308"},
        {"status": "Done", "count": 6, "color": "#22c55e"},
        {"status": "Testing", "count": 3, "color": "#06b6d4"}
    ]
}
```

#### GET /api/jira/by-sysfunc
Get defect counts grouped by system function.

**Query Parameters:** Same as /api/jira/overview

**Response:**
```json
{
    "sysfuncs": [
        {
            "acronym": "DLLR",
            "name": "Determine driver Lon_Lat Requests for parking function",
            "category": "Parking",
            "tester": "Suraj M",
            "open_count": 8,
            "closed_count": 4,
            "total": 12
        }
    ],
    "categories": ["Parking", "Miscellaneous", "Driving Function", "ODF", "ROV Functions Contributions"]
}
```

#### GET /api/jira/list
Get paginated defect list.

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `project_key` | string | "ADASDAI" | Jira project key |
| `release` | string | null | Release filter |
| `release_candidate` | string | null | Candidate filter |
| `safety_type` | string | null | Safety filter |
| `sysfunc` | string | null | System function filter (comma-separated) |
| `status` | string | null | "open" or "closed" |
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |

**Response:**
```json
{
    "issues": [
        {
            "key": "ADASDAI-313892",
            "summary": "internal signals not updated as expected values",
            "status": "Open",
            "status_color": "#eab308",
            "priority": "High",
            "priority_color": "#f97316",
            "assignee": "Kaushal Shetty",
            "reporter": "Suraj Miskin",
            "labels": ["DLLR", "SYS4_Bench_Test", "R18"],
            "latest_comment": {"body": "...", "author": "...", "created": "..."}
        }
    ],
    "total": 18,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
}
```

#### GET /api/jira/cache-clear
Clear Jira data cache (forces fresh fetch on next request).

**Response:**
```json
{"status": "ok", "message": "Cache cleared"}
```

---

## 6. Pydantic Models <a name="pydantic-models"></a>

```python
# models.py

import re
from pydantic import BaseModel, Field, field_validator

def strip_html(value: str) -> str:
    return re.sub(r'<[^>]+>', '', value).strip()

class CheckinRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    pc_type: str = Field(pattern="^(windows|linux)$")
    short_id: str = Field(min_length=1, max_length=50, pattern="^[A-Za-z0-9_]+$")
    purpose: str = Field(min_length=1, max_length=200)
    access_method: str = Field(pattern="^(rdp|nomachine|physical)$")

    @field_validator("purpose")
    @classmethod
    def sanitize_purpose(cls, v):
        return strip_html(v)

class CheckoutRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    pc_type: str = Field(pattern="^(windows|linux)$")

class ReleaseRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    requester_id: str = Field(min_length=1, max_length=50, pattern="^[A-Za-z0-9_]+$")
    purpose: str = Field(min_length=1, max_length=200)

class RestartRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    pc_type: str = Field(pattern="^(windows|linux)$")
```

---

## 7. Configuration Files <a name="configuration-files"></a>

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

### users.json
```json
{
    "users": {
        "ADPRIYA": {
            "name": "Adarsh Priyadarshi",
            "email": "adarsh.priyadarshi@mercedes-benz.com"
        }
    }
}
```

### credentials.json
```json
{
    "windows": {
        "default": {"username": "...", "password": "..."},
        "overrides": {"5": {"username": "...", "password": "..."}}
    },
    "linux": {
        "default": {"username": "...", "password": "..."},
        "overrides": {}
    }
}
```

### jira_config.json
```json
{
    "base_url": "https://mercedes-benz.atlassian.net",
    "user_email": "your.email@mercedes-benz.com",
    "api_token": "YOUR_JIRA_API_TOKEN",
    "project_key": "ADASDAI"
}
```
- `base_url`: Jira Cloud instance URL
- `user_email`: Email used for Jira API authentication
- `api_token`: Jira API token (generate from Atlassian account settings)
- `project_key`: Jira project to query defects from

---

## 8. Frontend Integration <a name="frontend-integration"></a>

### Dashboard Polling Mechanism

```javascript
// dashboard.js
const REFRESH_INTERVAL = 5000; // 5 seconds

async function fetchBenches() {
    const res = await fetch("/api/benches");
    const data = await res.json();
    renderDashboard(data);
}

setInterval(fetchBenches, REFRESH_INTERVAL);
```

### Adding a new UI element:

1. **HTML:** Edit `templates/dashboard.html`
2. **JavaScript:** Edit `static/js/dashboard.js`
3. **CSS:** Edit `static/css/dashboard.css`
4. **Data:** Add field to the API response in `bench_routes.py`

### Making API calls from frontend:

```javascript
// GET request
const res = await fetch("/api/your-endpoint?param=value");
const data = await res.json();

// POST request
const res = await fetch("/api/your-endpoint", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ key: "value" })
});
const data = await res.json();
```

---

## 9. How to Add a New Tool/Endpoint <a name="how-to-add-a-new-tool"></a>

### Method 1: Add to existing route file

**Step 1:** Open `routes/bench_routes.py`

**Step 2:** Add your endpoint:
```python
@router.post("/your-tool")
def your_tool(req: YourRequestModel):
    # Access bench metadata
    load_bench_meta()
    meta = BENCH_META.get(req.bench_id)
    
    # Access database
    benches = db.get_all_benches()
    
    # Your logic
    result = do_something(req.bench_id, req.param)
    
    return {"status": "ok", "data": result}
```

**Step 3:** Add validation model in `models.py`:
```python
class YourRequestModel(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    param: str = Field(min_length=1, max_length=100)
```

**Step 4:** Import model in route file:
```python
from models import CheckinRequest, CheckoutRequest, YourRequestModel
```

### Method 2: Create a new route file

**Step 1:** Create `routes/your_tool_routes.py`:
```python
from fastapi import APIRouter, HTTPException
import database as db

router = APIRouter(prefix="/api")

@router.get("/your-tool/status")
def get_tool_status():
    return {"status": "active"}

@router.post("/your-tool/execute")
def execute_tool(req: dict):
    bench_id = req.get("bench_id")
    # Your logic here
    return {"status": "ok"}
```

**Step 2:** Register in `main.py`:
```python
from routes.your_tool_routes import router as your_tool_router
app.include_router(your_tool_router)
```

**Step 3:** Restart server.

### Method 3: Add a new page

**Step 1:** Create template `templates/your_page.html`

**Step 2:** Add page route in `main.py`:
```python
@app.get("/your-page")
def your_page(request: Request):
    return templates.TemplateResponse(request=request, name="your_page.html")
```

**Step 3:** Add navigation link in dashboard header.

---

## 10. Integration Examples <a name="integration-examples"></a>

### Example 1: Add a "Bench Health" endpoint

A tool that checks if a bench is reachable via ping.

```python
# In routes/bench_routes.py

import subprocess

@router.get("/bench-health/{bench_id}")
def check_bench_health(bench_id: int):
    load_bench_meta()
    meta = BENCH_META.get(bench_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Bench not found")
    
    hostname = meta.get("windows_hostname", "")
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", hostname],
            capture_output=True, timeout=5
        )
        reachable = result.returncode == 0
    except:
        reachable = False
    
    return {
        "bench_id": bench_id,
        "hostname": hostname,
        "reachable": reachable
    }
```

### Example 2: Add a "Schedule Night Run" endpoint

```python
# In routes/bench_routes.py

@router.post("/schedule-run")
def schedule_run(req: dict):
    bench_id = req.get("bench_id")
    scheduled_time = req.get("time")  # e.g., "22:00"
    script_path = req.get("script")
    
    # Store in database or file
    # Set up a scheduler (e.g., APScheduler)
    
    return {"status": "ok", "message": f"Run scheduled at {scheduled_time}"}
```

### Example 3: Add data to dashboard cards

If your tool returns data that should appear on bench cards:

**Step 1:** Add to `/api/benches` response:
```python
# In bench_routes.py, get_benches() function
b["your_tool_data"] = get_your_tool_data(b["bench_id"])
```

**Step 2:** Display in frontend:
```javascript
// In dashboard.js, renderBenchCard() function
bodyHtml += `<div class="meta-row">Your Data: ${data.your_tool_data}</div>`;
```

### Example 4: External tool calling your API

Any external tool can integrate by making HTTP requests:

```python
import requests

# Check bench status
response = requests.get("http://c623drd41380439:8000/api/benches")
benches = response.json()

# Find available bench
available = [b for b in benches if b["status"] == "available" and b["pc_type"] == "windows"]

# Check in programmatically
requests.post("http://c623drd41380439:8000/api/checkin", json={
    "bench_id": available[0]["bench_id"],
    "pc_type": "windows",
    "short_id": "AUTOMATION",
    "purpose": "Automated Test Run",
    "access_method": "rdp"
})
```

---

## 11. Deployment & Server Management <a name="deployment"></a>

### Start Server
```bash
cd ~/Desktop/Bench_Usage_Automation/server
source venv/bin/activate
cd app
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### Stop Server
```bash
pkill -f "uvicorn main:app"
```

### Restart Server
```bash
pkill -f "uvicorn main:app"
cd ~/Desktop/Bench_Usage_Automation/server
source venv/bin/activate
cd app
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### Check Status
```bash
ps aux | grep uvicorn
curl --noproxy '*' http://localhost:8000/api/health
```

### View Logs
```bash
tail -50 ~/Desktop/Bench_Usage_Automation/server/app/server.log
```

### Install Dependencies
```bash
source venv/bin/activate
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY SOCKS_PROXY
pip install <package> --proxy "" --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### Database Operations
```bash
cd ~/Desktop/Bench_Usage_Automation/server/app

# View current bench status
sqlite3 bench_data.db "SELECT * FROM bench_status;"

# View recent history
sqlite3 bench_data.db "SELECT * FROM usage_history ORDER BY id DESC LIMIT 10;"

# Release a stuck bench
curl --noproxy '*' -X POST http://localhost:8000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"bench_id": 1, "pc_type": "windows"}'

# Clear all history
sqlite3 bench_data.db "DELETE FROM usage_history;"
```

---

## 12. Troubleshooting <a name="troubleshooting"></a>

| Issue | Solution |
|---|---|
| Server won't start (port in use) | `pkill -f "uvicorn main:app"` then restart |
| Import error on startup | Check `requirements.txt`, install missing packages |
| API returns 422 | Request body doesn't match Pydantic model — check required fields |
| CORS error in browser | Add your origin to `allow_origins` in `main.py` |
| Dashboard shows stale data | Check if server is running: `curl localhost:8000/api/health` |
| Bench stuck as occupied | Manual checkout: `POST /api/checkout` with bench_id and pc_type |
| Proxy issues with pip | Use `--proxy ""` flag and unset proxy environment variables |
| Database locked | Only one process should access SQLite at a time |

---

## Quick Reference Card

```
Server:       http://c623drd41380439:8000
API Docs:     http://c623drd41380439:8000/docs  (Swagger UI)
Dashboard:    http://c623drd41380439:8000/
History:      http://c623drd41380439:8000/history
Statistics:   http://c623drd41380439:8000/statistics
Defect Board: http://c623drd41380439:8000/defect-board

Python:       3.11 / 3.12
Framework:    FastAPI 0.115+
Database:     SQLite (bench data), Jira Cloud API (defects)
Server:       Uvicorn (ASGI)
OS:           Ubuntu Linux
Host:         c623drd41380439
Dependencies: httpx (Jira API calls), requests, pydantic, jinja2
```
