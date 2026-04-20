import json
import os
from fastapi import APIRouter, HTTPException
from models import CheckinRequest, CheckoutRequest
import database as db

router = APIRouter(prefix="/api")

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
BENCHES_CONFIG_PATH = os.path.join(CONFIG_DIR, "benches.json")
USERS_CONFIG_PATH = os.path.join(CONFIG_DIR, "users.json")

BENCH_META = {}
USER_MAP = {}


def load_bench_meta():
    global BENCH_META
    try:
        with open(BENCHES_CONFIG_PATH, "r") as f:
            data = json.load(f)
        for b in data.get("benches", []):
            BENCH_META[b["bench_id"]] = {
                "name": b.get("name", f"Bench {b['bench_id']}"),
                "alias": b.get("alias", ""),
                "windows_hostname": b.get("windows_hostname", ""),
                "windows_ip": b.get("windows_ip", ""),
                "linux_hostname": b.get("linux_hostname", ""),
                "linux_ip": b.get("linux_ip", ""),
                "licenses": b.get("licenses", {}),
            }
    except Exception:
        pass


def load_user_map():
    global USER_MAP
    try:
        with open(USERS_CONFIG_PATH, "r") as f:
            data = json.load(f)
        USER_MAP = data.get("users", {})
    except Exception:
        pass


load_bench_meta()
load_user_map()


@router.post("/checkin")
def checkin(req: CheckinRequest):
    benches = db.get_all_benches()
    for b in benches:
        if b["bench_id"] == req.bench_id and b["pc_type"] == req.pc_type:
            if b["status"] == "occupied":
                db.checkout(bench_id=req.bench_id, pc_type=req.pc_type)

    start_time = db.checkin(
        bench_id=req.bench_id,
        pc_type=req.pc_type,
        short_id=req.short_id.upper().strip(),
        purpose=req.purpose.strip(),
        access_method=req.access_method,
    )
    return {
        "status": "ok",
        "message": f"Checked in to Bench {req.bench_id} ({req.pc_type})",
        "start_time": start_time,
    }


@router.post("/checkout")
def checkout(req: CheckoutRequest):
    result = db.checkout(bench_id=req.bench_id, pc_type=req.pc_type)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Bench {req.bench_id} {req.pc_type} is not currently occupied",
        )
    return {
        "status": "ok",
        "message": f"Checked out from Bench {req.bench_id} ({req.pc_type})",
        **result,
    }


@router.get("/benches")
def get_benches():
    load_user_map()
    benches = db.get_all_benches()
    for b in benches:
        meta = BENCH_META.get(b["bench_id"], {})
        b["bench_name"] = meta.get("name", f"Bench {b['bench_id']}")
        b["bench_alias"] = meta.get("alias", "")
        b["win_hostname"] = meta.get("windows_hostname", "")
        b["lin_hostname"] = meta.get("linux_hostname", "")
        if b.get("short_id") and b["short_id"] in USER_MAP:
            b["user_email"] = USER_MAP[b["short_id"]].get("email", "")
            b["user_name"] = USER_MAP[b["short_id"]].get("name", "")
        else:
            b["user_email"] = ""
            b["user_name"] = ""
    return benches


@router.get("/bench/{bench_id}")
def get_bench_detail(bench_id: int):
    load_bench_meta()
    load_user_map()
    meta = BENCH_META.get(bench_id, {})
    if not meta:
        raise HTTPException(status_code=404, detail=f"Bench {bench_id} not found")

    benches = db.get_all_benches()
    pcs = {}
    for b in benches:
        if b["bench_id"] == bench_id:
            if b.get("short_id") and b["short_id"] in USER_MAP:
                b["user_email"] = USER_MAP[b["short_id"]].get("email", "")
                b["user_name"] = USER_MAP[b["short_id"]].get("name", "")
            else:
                b["user_email"] = ""
                b["user_name"] = ""
            pcs[b["pc_type"]] = b

    return {
        "bench_id": bench_id,
        "name": meta.get("name", f"Bench {bench_id}"),
        "alias": meta.get("alias", ""),
        "windows_hostname": meta.get("windows_hostname", ""),
        "windows_ip": meta.get("windows_ip", ""),
        "linux_hostname": meta.get("linux_hostname", ""),
        "linux_ip": meta.get("linux_ip", ""),
        "licenses": meta.get("licenses", {}),
        "pcs": pcs,
    }


@router.get("/health")
def health():
    return {"status": "ok", "service": "bench-usage-automation"}
