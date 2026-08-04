from pydantic import BaseModel

from .issue import UserInfo


class StatusDistribution(BaseModel):
    status: str
    category: str
    count: int
    color: str


class WorkloadEntry(BaseModel):
    assignee: UserInfo | None = None
    assignee_name: str = "Unassigned"
    todo: int = 0
    in_progress: int = 0
    done: int = 0
    total: int = 0


class TrendPoint(BaseModel):
    date: str
    created: int
    resolved: int


class VelocityEntry(BaseModel):
    sprint_name: str
    committed: int
    completed: int


class BurndownPoint(BaseModel):
    date: str
    remaining: float
    ideal: float


class AnalyticsOverview(BaseModel):
    total_issues: int
    todo_count: int
    in_progress_count: int
    done_count: int
    assignee_count: int
    status_distribution: list[StatusDistribution]
    workload: list[WorkloadEntry]


class BurndownResponse(BaseModel):
    sprint_name: str
    points: list[BurndownPoint]
    total_scope: float


class VelocityResponse(BaseModel):
    entries: list[VelocityEntry]


class TrendResponse(BaseModel):
    points: list[TrendPoint]
    period_days: int
