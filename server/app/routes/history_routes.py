from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
import database as db

router = APIRouter(prefix="/api")


@router.get("/history")
def get_history(
    bench_id: Optional[int] = Query(None, ge=1, le=5),
    short_id: Optional[str] = Query(None),
    limit: int = Query(100, le=2000),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    all_records = db.get_history(bench_id=bench_id, short_id=short_id, limit=limit,
                          date_from=date_from, date_to=date_to)
    return [r for r in all_records if r.get("pc_type") == "windows"]


@router.get("/statistics")
def get_statistics(
    bench_id: Optional[int] = Query(None, ge=1, le=5),
    short_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    if not date_from:
        date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    all_records = db.get_history(bench_id=bench_id, short_id=short_id, limit=2000,
                             date_from=date_from, date_to=date_to)
    records = [r for r in all_records if r.get("pc_type") == "windows"]

    total_sessions = len(records)
    total_duration = sum(r.get("duration_min") or 0 for r in records)
    avg_duration = round(total_duration / total_sessions, 1) if total_sessions else 0

    bench_hours = {}
    user_hours = {}
    day_counts = {}
    for r in records:
        bid = r.get("bench_id")
        dur = r.get("duration_min") or 0
        bench_hours[bid] = bench_hours.get(bid, 0) + dur
        uid = r.get("short_id", "")
        user_hours[uid] = user_hours.get(uid, 0) + dur
        if r.get("start_time"):
            day = r["start_time"][:10]
            day_counts[day] = day_counts.get(day, 0) + 1

    most_used_bench = max(bench_hours, key=bench_hours.get) if bench_hours else None
    busiest_day = max(day_counts, key=day_counts.get) if day_counts else None
    top_user = max(user_hours, key=user_hours.get) if user_hours else None

    return {
        "summary": {
            "total_sessions": total_sessions,
            "avg_duration_min": avg_duration,
            "total_duration_min": round(total_duration, 1),
            "most_used_bench": most_used_bench,
            "busiest_day": busiest_day,
            "top_user": top_user,
        },
        "records": records,
    }
