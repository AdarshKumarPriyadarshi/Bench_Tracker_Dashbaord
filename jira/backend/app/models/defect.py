from pydantic import BaseModel

from .issue import Issue


class AgingBucket(BaseModel):
    label: str
    count: int
    color: str


class PriorityCount(BaseModel):
    priority: str
    count: int
    color: str


class SysFuncCount(BaseModel):
    acronym: str
    name: str
    category: str
    open_count: int = 0
    closed_count: int = 0
    critical_count: int = 0
    total: int = 0


class DefectTrendPoint(BaseModel):
    date: str
    created: int
    resolved: int


class StatusCount(BaseModel):
    status: str
    count: int
    color: str


class DefectOverview(BaseModel):
    total: int
    open_count: int
    closed_count: int
    critical_count: int
    mttr_days: float
    aging: list[AgingBucket]
    priorities: list[PriorityCount]
    status_distribution: list[StatusCount]


class DefectBySysFuncResponse(BaseModel):
    sysfuncs: list[SysFuncCount]


class DefectListResponse(BaseModel):
    issues: list[Issue]
    total: int
    page: int
    page_size: int
    total_pages: int


class DefectTrendResponse(BaseModel):
    points: list[DefectTrendPoint]
    period_days: int
