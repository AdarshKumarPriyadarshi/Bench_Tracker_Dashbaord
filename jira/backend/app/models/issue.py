from pydantic import BaseModel


class StatusInfo(BaseModel):
    name: str
    category: str  # "todo", "in_progress", "done"
    color: str


class UserInfo(BaseModel):
    account_id: str
    display_name: str
    email: str = ""
    avatar_url: str = ""


class SprintRef(BaseModel):
    id: int
    name: str
    state: str  # "active", "closed", "future"


class LatestComment(BaseModel):
    body: str
    author: str
    created: str


class Issue(BaseModel):
    key: str
    id: str
    summary: str
    status: StatusInfo
    assignee: UserInfo | None = None
    reporter: UserInfo | None = None
    labels: list[str] = []
    priority: str = "Medium"
    issue_type: str = "Task"
    created: str = ""
    updated: str = ""
    sprint: SprintRef | None = None
    story_points: float | None = None
    latest_comment: LatestComment | None = None


class IssueListResponse(BaseModel):
    issues: list[Issue]
    total: int
    page: int
    page_size: int
    total_pages: int
