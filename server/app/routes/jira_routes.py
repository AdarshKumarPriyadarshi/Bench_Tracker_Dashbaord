"""
Jira Defect Board API routes.
Ports the logic from the standalone jira/ project into the bench dashboard server.
"""

import os
import json
import math
import time
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException
import httpx

router = APIRouter(prefix="/api/jira")

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
JIRA_CONFIG_PATH = os.path.join(CONFIG_DIR, "jira_config.json")

SYSFUNC_LABELS = [
    "Dimming", "PRD", "GTS", "POM", "PDD", "PSSDS", "DLCS", "DLLR",
    "SSPN", "SEM_ROV", "ODF", "Presafe", "Visualisation", "CCHP",
    "PTS_Op_Mode", "SVS_Op_Mode", "ALSA", "PWD", "AR", "VRP", "VBPS",
]

SYSFUNC_MAP = {
    "Dimming": {"name": "Provide Inputs for Dimming Functions", "category": "Miscellaneous", "tester": "Suraj M"},
    "PRD": {"name": "Provide Radar Data", "category": "Miscellaneous", "tester": "Vysiya S"},
    "GTS": {"name": "Determine Global Time Sync", "category": "Miscellaneous", "tester": "Vysiya S"},
    "POM": {"name": "Determine Parking Operation Mode", "category": "Parking", "tester": "Surya J"},
    "PDD": {"name": "Provide Image And Video Data for Park Damage Detection", "category": "Parking", "tester": "Surya J & Nayaz"},
    "PSSDS": {"name": "Provide System state and Degradation state", "category": "Parking", "tester": "Rahul G"},
    "DLCS": {"name": "Determine Driver Lon Control state for parking function", "category": "Parking", "tester": "Surya J"},
    "DLLR": {"name": "Determine driver Lon_Lat Requests for parking function", "category": "Parking", "tester": "Suraj M"},
    "SSPN": {"name": "Startup/Shutdown/PNC", "category": "Miscellaneous", "tester": "Vysiya S"},
    "SEM_ROV": {"name": "SEM: ROV DTC", "category": "Miscellaneous", "tester": "Rahul G & Bharath"},
    "ODF": {"name": "ODF - Provide Function Codifications System Function Content", "category": "ODF", "tester": "Nayaz"},
    "Presafe": {"name": "Provide Inputs for PreSafe Functions", "category": "ROV Functions Contributions", "tester": "Sushma Y S"},
    "Visualisation": {"name": "Coordinate in-vehicle Driver interactions and visualization", "category": "Parking", "tester": "Rahul G, Surya & Sushma, Kajal"},
    "CCHP": {"name": "Coordinate Cleaning Heating and Precondition", "category": "Miscellaneous", "tester": "Bharath B"},
    "PTS_Op_Mode": {"name": "Determine PTS Operation Mode", "category": "Parking", "tester": "Rahul G"},
    "SVS_Op_Mode": {"name": "Determine SVS Operation Mode", "category": "Parking", "tester": "Surya J"},
    "ALSA": {"name": "Execute Driver Warning Cascade for ALSA", "category": "Driving Function", "tester": "Kajal K"},
    "PWD": {"name": "Provide Weather Data", "category": "Miscellaneous", "tester": "Bharath B"},
    "AR": {"name": "Argumented Reality", "category": "Parking", "tester": "Sushma Y S & Kajal K"},
    "VRP": {"name": "Visual RIM Protection", "category": "Parking", "tester": "Vysiya S"},
    "VBPS": {"name": "Determine Vehicle Body parts", "category": "Parking", "tester": "Bharath B"},
}

PRIORITY_COLORS = {
    "Highest": "#dc2626",
    "High": "#f97316",
    "Medium": "#eab308",
    "Low": "#3b82f6",
    "Lowest": "#94a3b8",
}

STATUS_COLORS = {
    "Open": "#eab308",
    "Refinement": "#8b5cf6",
    "To Do": "#f97316",
    "In Progress": "#3b82f6",
    "Blocked (Migrated)": "#ef4444",
    "Testing": "#06b6d4",
    "Done": "#22c55e",
    "Under Observation": "#14b8a6",
    "Reopened": "#ec4899",
    "Rejected": "#dc2626",
    "Closed": "#10b981",
}

CATEGORIES = ["Parking", "Miscellaneous", "Driving Function", "ODF", "ROV Functions Contributions"]


# --- In-memory cache ---
_cache = {}
_cache_ttl = 180


def cache_get(key):
    if key not in _cache:
        return None
    value, expires_at = _cache[key]
    if time.time() > expires_at:
        del _cache[key]
        return None
    return value


def cache_set(key, value, ttl=None):
    expires_at = time.time() + (ttl or _cache_ttl)
    _cache[key] = (value, expires_at)


def cache_clear():
    _cache.clear()


# --- Jira config loading ---
def load_jira_config():
    try:
        with open(JIRA_CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


# --- Jira Client (same pattern as jira/backend/app/services/jira_client.py) ---
class JiraClient:
    def __init__(self):
        config = load_jira_config()
        self.base_url = config.get("base_url", "https://mercedes-benz.atlassian.net")
        self.auth = (config.get("user_email", ""), config.get("api_token", ""))
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=self.auth,
            headers=self.headers,
            timeout=30.0,
        )

    async def search_issues(self, jql, fields=None, start_at=0, max_results=50):
        if not self.auth[0] or not self.auth[1]:
            raise HTTPException(status_code=500, detail="Jira credentials not configured")

        if fields is None:
            fields = ["summary", "status", "assignee", "labels", "priority", "created", "updated", "reporter", "comment"]

        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "startAt": start_at,
            "maxResults": max_results,
        }

        async with self._client() as client:
            response = await client.get(url, params=params)
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Jira authentication failed")
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"Jira API error: {response.text[:200]}")
            return response.json()


# --- Issue mapper (same as jira/backend/app/core/jira_mapper.py) ---
def map_issue(raw):
    fields = raw.get("fields", {})
    status_raw = fields.get("status", {})
    priority_raw = fields.get("priority", {})
    assignee_raw = fields.get("assignee")
    reporter_raw = fields.get("reporter")

    latest_comment = None
    comment_field = fields.get("comment")
    if comment_field and isinstance(comment_field, dict):
        comments = comment_field.get("comments", [])
        if comments:
            last = comments[-1]
            body_raw = last.get("body", "")
            if isinstance(body_raw, dict):
                content = body_raw.get("content", [])
                text_parts = []
                for block in content:
                    for item in block.get("content", []):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                body_text = " ".join(text_parts)
            else:
                body_text = str(body_raw)
            latest_comment = {
                "body": body_text[:200],
                "author": last.get("author", {}).get("displayName", "Unknown"),
                "created": last.get("created", ""),
            }

    return {
        "key": raw.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": status_raw.get("name", "Unknown"),
        "status_color": STATUS_COLORS.get(status_raw.get("name", ""), "#94a3b8"),
        "priority": priority_raw.get("name", "Medium") if priority_raw else "Medium",
        "priority_color": PRIORITY_COLORS.get(priority_raw.get("name", "Medium") if priority_raw else "Medium", "#94a3b8"),
        "assignee": assignee_raw.get("displayName", "Unassigned") if assignee_raw else "Unassigned",
        "reporter": reporter_raw.get("displayName", "Unknown") if reporter_raw else "Unknown",
        "labels": fields.get("labels", []),
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
        "latest_comment": latest_comment,
    }


# --- JQL builder (same as jira/backend/app/services/defect_service.py) ---
def build_base_jql(project_key, release=None, release_candidate=None, safety_type=None):
    labels_str = ", ".join(SYSFUNC_LABELS)
    jql = f'project = {project_key} AND issuetype = Bug AND labels = "SYS4_Bench_Test" AND labels in ({labels_str})'
    if release:
        jql += f' AND labels = "{release}"'
    if release_candidate:
        jql += f' AND labels = "{release_candidate}"'
    if safety_type:
        jql += f' AND labels = "{safety_type}"'
    return jql


# --- Fetch all defects (with caching) ---
async def fetch_all_defects(project_key, release=None, release_candidate=None, safety_type=None):
    cache_key = f"defects:{project_key}:{release or 'all'}:{release_candidate or 'all'}:{safety_type or 'all'}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    jira = JiraClient()
    jql = build_base_jql(project_key, release, release_candidate, safety_type) + " ORDER BY updated DESC"
    all_issues = []
    start_at = 0

    while True:
        data = await jira.search_issues(
            jql=jql,
            fields=["summary", "status", "assignee", "labels", "priority", "created", "updated", "reporter", "comment"],
            start_at=start_at,
            max_results=100,
        )
        issues = [map_issue(raw) for raw in data.get("issues", [])]
        all_issues.extend(issues)
        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= total or not issues:
            break

    cache_set(cache_key, all_issues)
    return all_issues


# --- API Endpoints ---

@router.get("/overview")
async def get_overview(
    project_key: str = Query("ADASDAI"),
    release: str = Query(None),
    release_candidate: str = Query(None),
    safety_type: str = Query(None),
):
    all_issues = await fetch_all_defects(project_key, release, release_candidate, safety_type)

    closed = [i for i in all_issues if i["status"] == "Closed"]
    ongoing = [i for i in all_issues if i["status"] != "Closed"]

    now = datetime.now()
    aging_buckets = {"0-7d": 0, "7-14d": 0, "14-30d": 0, "30d+": 0}
    for issue in all_issues:
        if issue["created"]:
            try:
                created = datetime.fromisoformat(issue["created"].replace("Z", "+00:00")).replace(tzinfo=None)
                age = (now - created).days
                if age <= 7:
                    aging_buckets["0-7d"] += 1
                elif age <= 14:
                    aging_buckets["7-14d"] += 1
                elif age <= 30:
                    aging_buckets["14-30d"] += 1
                else:
                    aging_buckets["30d+"] += 1
            except (ValueError, TypeError):
                pass

    priority_counts = defaultdict(int)
    for issue in all_issues:
        priority_counts[issue["priority"]] += 1

    status_counts = defaultdict(int)
    for issue in ongoing:
        status_counts[issue["status"]] += 1

    return {
        "total": len(all_issues),
        "ongoing_count": len(ongoing),
        "closed_count": len(closed),
        "aging": [
            {"label": "0-7d", "count": aging_buckets["0-7d"], "color": "#22c55e"},
            {"label": "7-14d", "count": aging_buckets["7-14d"], "color": "#eab308"},
            {"label": "14-30d", "count": aging_buckets["14-30d"], "color": "#f97316"},
            {"label": "30d+", "count": aging_buckets["30d+"], "color": "#dc2626"},
        ],
        "priorities": [
            {"priority": p, "count": c, "color": PRIORITY_COLORS.get(p, "#94a3b8")}
            for p, c in sorted(priority_counts.items(), key=lambda x: list(PRIORITY_COLORS.keys()).index(x[0]) if x[0] in PRIORITY_COLORS else 99)
        ],
        "status_distribution": [
            {"status": s, "count": c, "color": STATUS_COLORS.get(s, "#94a3b8")}
            for s, c in status_counts.items()
        ],
    }


@router.get("/by-sysfunc")
async def get_by_sysfunc(
    project_key: str = Query("ADASDAI"),
    release: str = Query(None),
    release_candidate: str = Query(None),
    safety_type: str = Query(None),
):
    all_issues = await fetch_all_defects(project_key, release, release_candidate, safety_type)

    counts = {}
    for acronym, info in SYSFUNC_MAP.items():
        counts[acronym] = {
            "acronym": acronym,
            "name": info["name"],
            "category": info["category"],
            "tester": info["tester"],
            "open_count": 0,
            "closed_count": 0,
            "total": 0,
        }

    for issue in all_issues:
        for label in issue["labels"]:
            if label in counts:
                counts[label]["total"] += 1
                if issue["status"] == "Closed":
                    counts[label]["closed_count"] += 1
                else:
                    counts[label]["open_count"] += 1

    sysfuncs = sorted(counts.values(), key=lambda s: s["total"], reverse=True)
    return {"sysfuncs": sysfuncs, "categories": CATEGORIES}


@router.get("/list")
async def get_defect_list(
    project_key: str = Query("ADASDAI"),
    release: str = Query(None),
    release_candidate: str = Query(None),
    safety_type: str = Query(None),
    sysfunc: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    jira = JiraClient()
    jql = build_base_jql(project_key, release, release_candidate, safety_type)
    if sysfunc:
        if "," in sysfunc:
            labels = ", ".join(f'"{l.strip()}"' for l in sysfunc.split(","))
            jql += f" AND labels in ({labels})"
        else:
            jql += f' AND labels = "{sysfunc}"'
    if status == "open":
        jql += ' AND status != "Closed"'
    elif status == "closed":
        jql += ' AND status = "Closed"'
    jql += " ORDER BY priority DESC, updated DESC"

    start_at = (page - 1) * page_size
    data = await jira.search_issues(jql=jql, start_at=start_at, max_results=page_size)

    issues = [map_issue(raw) for raw in data.get("issues", [])]
    total = data.get("total", 0)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return {
        "issues": issues,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/cache-clear")
async def clear_cache():
    cache_clear()
    return {"status": "ok", "message": "Cache cleared"}
