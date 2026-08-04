import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional


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


class HistoryQuery(BaseModel):
    bench_id: Optional[int] = None
    short_id: Optional[str] = None
    limit: int = Field(default=100, le=500)


class ReleaseRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    requester_id: str = Field(min_length=1, max_length=50, pattern="^[A-Za-z0-9_]+$")
    purpose: str = Field(min_length=1, max_length=200)

    @field_validator("purpose")
    @classmethod
    def sanitize_purpose(cls, v):
        return strip_html(v)


class RestartRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    pc_type: str = Field(pattern="^(windows|linux)$")
