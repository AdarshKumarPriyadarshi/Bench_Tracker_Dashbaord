from collections import defaultdict
from datetime import datetime, timedelta

from app.services.jira_client import JiraClient
from app.services.cache_service import cache
from app.core.jira_mapper import map_issue
from app.core.pagination import paginate
from app.models.issue import Issue
from app.models.defect import (
    DefectOverview,
    AgingBucket,
    PriorityCount,
    SysFuncCount,
    DefectBySysFuncResponse,
    DefectListResponse,
    DefectTrendPoint,
    DefectTrendResponse,
)

SYSFUNC_LABELS = [
    "Dimming", "PRD", "GTS", "POM", "PDD", "PSSDS", "DLCS", "DLLR",
    "SSPN", "SEM_ROV", "ODF", "Presafe", "Visualisation", "CCHP",
    "PTS_Op_Mode", "SVS_Op_Mode", "ALSA", "PWD", "AR", "VRP", "VBPS",
]

SYSFUNC_MAP = {
    "Dimming": {"name": "Provide Inputs for Dimming Functions", "category": "Miscellaneous"},
    "PRD": {"name": "Provide Radar Data", "category": "Miscellaneous"},
    "GTS": {"name": "Determine Global Time Sync", "category": "Miscellaneous"},
    "POM": {"name": "Determine Parking Operation Mode", "category": "Parking"},
    "PDD": {"name": "Provide Image And Video Data for Park Damage Detection", "category": "Parking"},
    "PSSDS": {"name": "Provide System state and Degradation state", "category": "Parking"},
    "DLCS": {"name": "Determine Driver Lon Control state for parking function", "category": "Parking"},
    "DLLR": {"name": "Determine driver Lon_Lat Requests for parking function", "category": "Parking"},
    "SSPN": {"name": "Startup/Shutdown/PNC", "category": "Miscellaneous"},
    "SEM_ROV": {"name": "SEM: ROV DTC", "category": "Miscellaneous"},
    "ODF": {"name": "ODF - Provide Function Codifications System Function Content", "category": "ODF"},
    "Presafe": {"name": "Provide Inputs for PreSafe Functions", "category": "ROV Functions Contributions"},
    "Visualisation": {"name": "Coordinate in-vehicle Driver interactions and visualization", "category": "Parking"},
    "CCHP": {"name": "Coordinate Cleaning Heating and Precondition", "category": "Miscellaneous"},
    "PTS_Op_Mode": {"name": "Determine PTS Operation Mode", "category": "Parking"},
    "SVS_Op_Mode": {"name": "Determine SVS Operation Mode", "category": "Parking"},
    "ALSA": {"name": "Execute Driver Warning Cascade for ALSA", "category": "Driving Function"},
    "PWD": {"name": "Provide Weather Data", "category": "Miscellaneous"},
    "AR": {"name": "Argumented Reality", "category": "Parking"},
    "VRP": {"name": "Visual RIM Protection", "category": "Parking"},
    "VBPS": {"name": "Determine Vehicle Body parts", "category": "Parking"},
}

PRIORITY_COLORS = {
    "Highest": "#dc2626",
    "High": "#f97316",
    "Medium": "#eab308",
    "Low": "#3b82f6",
    "Lowest": "#94a3b8",
}


class DefectService:
    def __init__(self, client: JiraClient):
        self.client = client

    def _build_base_jql(self, project_key: str, release: str | None = None, release_candidate: str | None = None, safety_type: str | None = None) -> str:
        labels_str = ", ".join(SYSFUNC_LABELS)
        jql = f"project = {project_key} AND issuetype = Bug AND labels = \"SYS4_Bench_Test\" AND labels in ({labels_str})"
        if release:
            jql += f' AND labels = "{release}"'
        if release_candidate:
            jql += f' AND labels = "{release_candidate}"'
        if safety_type:
            jql += f' AND labels = "{safety_type}"'
        return jql

    async def _fetch_all_defects(self, project_key: str, release: str | None = None, release_candidate: str | None = None, safety_type: str | None = None) -> list[Issue]:
        cache_key = f"defects_all:{project_key}:{release or 'all'}:{release_candidate or 'all'}:{safety_type or 'all'}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        jql = self._build_base_jql(project_key, release, release_candidate, safety_type) + " ORDER BY updated DESC"
        all_issues: list[Issue] = []
        start_at = 0
        while True:
            data = await self.client.search_issues(
                jql=jql,
                fields=["summary", "status", "assignee", "labels", "priority", "created", "updated", "resolutiondate", "reporter", "comment"],
                start_at=start_at,
                max_results=100,
            )
            issues = [map_issue(raw) for raw in data.get("issues", [])]
            all_issues.extend(issues)
            total = data.get("total", 0)
            start_at += len(issues)
            if start_at >= total or not issues:
                break

        cache.set(cache_key, all_issues, ttl=180)
        return all_issues

    async def get_overview(self, project_key: str, release: str | None = None, release_candidate: str | None = None, safety_type: str | None = None) -> DefectOverview:
        all_issues = await self._fetch_all_defects(project_key, release, release_candidate, safety_type)

        closed_issues = [i for i in all_issues if i.status.name == "Closed"]
        open_issues = [i for i in all_issues if i.status.name != "Closed"]
        critical = [i for i in all_issues if i.priority in ("Highest", "Critical")]

        now = datetime.now()
        aging_buckets = {"0-7d": 0, "7-14d": 0, "14-30d": 0, "30d+": 0}
        resolution_days: list[float] = []

        for issue in all_issues:
            if issue.created:
                try:
                    created = datetime.fromisoformat(issue.created.replace("Z", "+00:00")).replace(tzinfo=None)
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

            if issue.status.name == "Closed" and issue.created and issue.updated:
                try:
                    created = datetime.fromisoformat(issue.created.replace("Z", "+00:00")).replace(tzinfo=None)
                    resolved = datetime.fromisoformat(issue.updated.replace("Z", "+00:00")).replace(tzinfo=None)
                    resolution_days.append((resolved - created).days)
                except (ValueError, TypeError):
                    pass

        mttr = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else 0.0

        aging = [
            AgingBucket(label="0-7d", count=aging_buckets["0-7d"], color="#22c55e"),
            AgingBucket(label="7-14d", count=aging_buckets["7-14d"], color="#eab308"),
            AgingBucket(label="14-30d", count=aging_buckets["14-30d"], color="#f97316"),
            AgingBucket(label="30d+", count=aging_buckets["30d+"], color="#dc2626"),
        ]

        priority_counts: dict[str, int] = defaultdict(int)
        for issue in all_issues:
            priority_counts[issue.priority] += 1

        priorities = [
            PriorityCount(priority=p, count=c, color=PRIORITY_COLORS.get(p, "#94a3b8"))
            for p, c in sorted(priority_counts.items(), key=lambda x: list(PRIORITY_COLORS.keys()).index(x[0]) if x[0] in PRIORITY_COLORS else 99)
        ]

        status_color_map = {
            "Open": "#64748b",
            "Refinement": "#8b5cf6",
            "To Do": "#f59e0b",
            "In Progress": "#3b82f6",
            "Blocked (Migrated)": "#ef4444",
            "Testing": "#06b6d4",
            "Done": "#22c55e",
            "Under Observation": "#f97316",
            "Reopened": "#ec4899",
            "Rejected": "#6b7280",
            "Closed": "#10b981",
        }

        from app.models.defect import StatusCount
        status_counts: dict[str, int] = defaultdict(int)
        for issue in all_issues:
            status_counts[issue.status.name] += 1

        status_distribution = [
            StatusCount(status=s, count=c, color=status_color_map.get(s, "#94a3b8"))
            for s, c in status_counts.items()
        ]

        return DefectOverview(
            total=len(all_issues),
            open_count=len(open_issues),
            closed_count=len(closed_issues),
            critical_count=len(critical),
            mttr_days=mttr,
            aging=aging,
            priorities=priorities,
            status_distribution=status_distribution,
        )

    async def get_by_sysfunc(self, project_key: str, release: str | None = None, release_candidate: str | None = None, safety_type: str | None = None) -> DefectBySysFuncResponse:
        all_issues = await self._fetch_all_defects(project_key, release, release_candidate, safety_type)

        counts: dict[str, SysFuncCount] = {}
        for acronym, info in SYSFUNC_MAP.items():
            counts[acronym] = SysFuncCount(
                acronym=acronym,
                name=info["name"],
                category=info["category"],
            )

        for issue in all_issues:
            for label in issue.labels:
                if label in counts:
                    entry = counts[label]
                    entry.total += 1
                    if issue.status.name == "Closed":
                        entry.closed_count += 1
                    else:
                        entry.open_count += 1
                    if issue.priority in ("Highest", "Critical"):
                        entry.critical_count += 1

        sysfuncs = sorted(counts.values(), key=lambda s: s.total, reverse=True)
        return DefectBySysFuncResponse(sysfuncs=sysfuncs)

    async def get_list(
        self,
        project_key: str,
        release: str | None = None,
        release_candidate: str | None = None,
        safety_type: str | None = None,
        sysfunc: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DefectListResponse:
        jql = self._build_base_jql(project_key, release, release_candidate, safety_type)
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

        data = await self.client.search_issues(
            jql=jql,
            fields=["summary", "status", "assignee", "labels", "priority", "created", "updated", "reporter", "comment"],
            start_at=start_at,
            max_results=page_size,
        )

        issues = [map_issue(raw) for raw in data.get("issues", [])]
        total = data.get("total", 0)
        meta = paginate(total, page, page_size)

        return DefectListResponse(issues=issues, **meta)

    async def get_trend(self, project_key: str, days: int = 7, release: str | None = None, release_candidate: str | None = None, safety_type: str | None = None) -> DefectTrendResponse:
        start_date = datetime.now() - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")

        base_jql = self._build_base_jql(project_key, release, release_candidate, safety_type)
        created_jql = f'{base_jql} AND created >= "{start_str}" ORDER BY created ASC'
        resolved_jql = f'{base_jql} AND resolved >= "{start_str}" ORDER BY resolved ASC'

        created_data = await self.client.search_issues(jql=created_jql, fields=["created"], max_results=100)
        resolved_data = await self.client.search_issues(jql=resolved_jql, fields=["resolutiondate"], max_results=100)

        created_by_date: dict[str, int] = defaultdict(int)
        for raw in created_data.get("issues", []):
            created_str = raw.get("fields", {}).get("created", "")
            if created_str:
                created_by_date[created_str[:10]] += 1

        resolved_by_date: dict[str, int] = defaultdict(int)
        for raw in resolved_data.get("issues", []):
            res_str = raw.get("fields", {}).get("resolutiondate", "")
            if res_str:
                resolved_by_date[res_str[:10]] += 1

        points: list[DefectTrendPoint] = []
        for day_offset in range(days + 1):
            current_date = start_date + timedelta(days=day_offset)
            date_key = current_date.strftime("%Y-%m-%d")
            points.append(DefectTrendPoint(
                date=date_key,
                created=created_by_date.get(date_key, 0),
                resolved=resolved_by_date.get(date_key, 0),
            ))

        return DefectTrendResponse(points=points, period_days=days)
