import json
import os
import logging
import subprocess
from fastapi import APIRouter, HTTPException
from models import CheckinRequest, CheckoutRequest, ReleaseRequest, RestartRequest
import database as db

router = APIRouter(prefix="/api")

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
BENCHES_CONFIG_PATH = os.path.join(CONFIG_DIR, "benches.json")
USERS_CONFIG_PATH = os.path.join(CONFIG_DIR, "users.json")
CREDENTIALS_PATH = os.path.join(CONFIG_DIR, "credentials.json")

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
                "architecture": b.get("architecture", ""),
                "sw_version": b.get("sw_version", ""),
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

    other_pc = "linux" if req.pc_type == "windows" else "windows"
    for b in benches:
        if b["bench_id"] == req.bench_id and b["pc_type"] == other_pc:
            if b["status"] == "occupied":
                db.checkout(bench_id=req.bench_id, pc_type=other_pc)
    db.checkin(
        bench_id=req.bench_id,
        pc_type=other_pc,
        short_id=req.short_id.upper().strip(),
        purpose=req.purpose.strip(),
        access_method=req.access_method,
    )

    return {
        "status": "ok",
        "message": f"Checked in to Bench {req.bench_id} (both PCs)",
        "start_time": start_time,
    }


@router.post("/checkout")
def checkout(req: CheckoutRequest):
    result = db.checkout(bench_id=req.bench_id, pc_type=req.pc_type)

    other_pc = "linux" if req.pc_type == "windows" else "windows"
    db.checkout(bench_id=req.bench_id, pc_type=other_pc)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Bench {req.bench_id} {req.pc_type} is not currently occupied",
        )
    return {
        "status": "ok",
        "message": f"Checked out from Bench {req.bench_id} (both PCs)",
        **result,
    }


@router.get("/benches")
def get_benches():
    load_user_map()
    load_bench_meta()
    benches = db.get_all_benches()
    for b in benches:
        meta = BENCH_META.get(b["bench_id"], {})
        b["bench_name"] = meta.get("name", f"Bench {b['bench_id']}")
        b["bench_alias"] = meta.get("alias", "")
        b["architecture"] = meta.get("architecture", "")
        b["sw_version"] = meta.get("sw_version", "")
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
        "architecture": meta.get("architecture", ""),
        "sw_version": meta.get("sw_version", ""),
        "windows_hostname": meta.get("windows_hostname", ""),
        "windows_ip": meta.get("windows_ip", ""),
        "linux_hostname": meta.get("linux_hostname", ""),
        "linux_ip": meta.get("linux_ip", ""),
        "licenses": meta.get("licenses", {}),
        "pcs": pcs,
    }


@router.post("/request-release")
def request_release(req: ReleaseRequest):
    bench_id = req.bench_id
    requester_id = req.requester_id
    purpose = req.purpose

    benches = db.get_all_benches()
    occupant = None
    for b in benches:
        if b["bench_id"] == bench_id and b["pc_type"] == "windows" and b["status"] == "occupied":
            occupant = b["short_id"]
            break

    if not occupant:
        raise HTTPException(status_code=404, detail="Bench is not currently occupied")

    bench_name = BENCH_META.get(bench_id, {}).get("name", f"Bench {bench_id}")
    logging.info(f"Release request: {requester_id} wants {bench_name} (occupied by {occupant}). Reason: {purpose}")

    return {
        "status": "ok",
        "message": f"Request sent to {occupant}",
        "occupant": occupant,
        "bench_name": bench_name,
    }


@router.post("/restart-bench")
def restart_bench(req: RestartRequest):
    bench_id = req.bench_id
    pc_type = req.pc_type

    load_bench_meta()
    meta = BENCH_META.get(bench_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Bench not found")

    benches = db.get_all_benches()
    for b in benches:
        if b["bench_id"] == bench_id and b["pc_type"] == "windows" and b["status"] == "occupied":
            raise HTTPException(status_code=400, detail="Cannot restart - bench is currently occupied")

    hostname = meta.get("windows_hostname", "") if pc_type == "windows" else meta.get("linux_hostname", "")
    if not hostname:
        raise HTTPException(status_code=400, detail=f"No {pc_type} hostname configured for this bench")

    try:
        with open(CREDENTIALS_PATH, "r") as f:
            creds = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Credentials config not found")

    pc_creds = creds.get(pc_type, {})
    bench_creds = pc_creds.get("overrides", {}).get(str(bench_id))
    if not bench_creds or not bench_creds.get("username"):
        bench_creds = pc_creds.get("default", {})

    username = bench_creds.get("username", "")
    password = bench_creds.get("password", "")
    if not username or not password:
        raise HTTPException(status_code=500, detail=f"{pc_type} credentials not configured")

    bench_name = meta.get("name", f"Bench {bench_id}")
    logging.info(f"Restarting bench {bench_id} {pc_type} ({hostname})")

    if pc_type == "windows":
        cmd = ["net", "rpc", "shutdown", "-r", "-f", "-I", hostname, "-U", f"{username}%{password}"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if "succeeded" in result.stdout.lower() or result.returncode == 0:
                logging.info(f"Windows restart successful for bench {bench_id}")
                return {"status": "ok", "message": f"Restart signal sent to {bench_name} (Windows)"}
            else:
                error = result.stderr.strip() or result.stdout.strip()
                logging.error(f"Windows restart failed for bench {bench_id}: {error}")
                raise HTTPException(status_code=500, detail="Restart failed. Please try again.")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Restart command timed out")
    else:
        cmd = ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
               f"{username}@{hostname}", f"echo '{password}' | sudo -S reboot"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 or "closed by remote" in result.stderr.lower():
                logging.info(f"Linux restart successful for bench {bench_id}")
                return {"status": "ok", "message": f"Restart signal sent to {bench_name} (Linux)"}
            else:
                error = result.stderr.strip() or result.stdout.strip()
                logging.error(f"Linux restart failed for bench {bench_id}: {error}")
                raise HTTPException(status_code=500, detail="Restart failed. Please try again.")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Restart command timed out")


@router.get("/users")
def get_users():
    load_user_map()
    return [{"short_id": k, "name": v.get("name", "")} for k, v in USER_MAP.items()]


@router.post("/update-bench-sw")
def update_bench_sw(req: dict):
    bench_id = req.get("bench_id")
    sw_version = req.get("sw_version")
    architecture = req.get("architecture")

    if not all([bench_id, sw_version, architecture]):
        raise HTTPException(status_code=400, detail="Missing fields")

    with open(BENCHES_CONFIG_PATH, "r") as f:
        data = json.load(f)

    updated = False
    for bench in data["benches"]:
        if bench["bench_id"] == bench_id:
            bench["sw_version"] = sw_version
            bench["architecture"] = architecture
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Bench not found")

    with open(BENCHES_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

    load_bench_meta()
    logging.info(f"Bench {bench_id} SW updated to {sw_version} ({architecture})")
    return {"status": "ok", "message": f"Bench {bench_id} updated to {sw_version} ({architecture})"}


@router.get("/health")
def health():
    return {"status": "ok", "service": "bench-usage-automation"}
