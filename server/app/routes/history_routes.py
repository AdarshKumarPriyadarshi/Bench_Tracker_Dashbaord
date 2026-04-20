from fastapi import APIRouter, Query
from typing import Optional
import database as db

router = APIRouter(prefix="/api")


@router.get("/history")
def get_history(
    bench_id: Optional[int] = Query(None, ge=1, le=5),
    short_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    return db.get_history(bench_id=bench_id, short_id=short_id, limit=limit,
                          date_from=date_from, date_to=date_to)
