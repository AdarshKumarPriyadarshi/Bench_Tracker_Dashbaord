from pydantic import BaseModel, Field
from typing import Optional


class CheckinRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    pc_type: str = Field(pattern="^(windows|linux)$")
    short_id: str = Field(min_length=1, max_length=50)
    purpose: str = Field(min_length=1, max_length=200)
    access_method: str = Field(pattern="^(rdp|nomachine|physical)$")


class CheckoutRequest(BaseModel):
    bench_id: int = Field(ge=1, le=5)
    pc_type: str = Field(pattern="^(windows|linux)$")


class HistoryQuery(BaseModel):
    bench_id: Optional[int] = None
    short_id: Optional[str] = None
    limit: int = Field(default=100, le=500)
