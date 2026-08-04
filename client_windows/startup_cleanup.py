"""
Runs at system boot (before any user logs in).
Clears stale lock files and sends checkout to release bench on dashboard.
"""
import os
import sys
import configparser
import time

try:
    import requests
except ImportError:
    requests = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")

# Delete stale lock files
for lock in [".session_monitor.lock", ".login_gate.lock"]:
    path = os.path.join(SCRIPT_DIR, lock)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# Send checkout to release bench on dashboard
if requests:
    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)
        server_url = config.get("server", "url", fallback="http://localhost:8000")
        bench_id = config.getint("bench", "bench_id", fallback=1)

        time.sleep(10)  # Wait for network to be ready

        resp = requests.post(
            f"{server_url}/api/checkout",
            json={"bench_id": bench_id, "pc_type": "windows"},
            timeout=15,
            proxies={"http": None, "https": None},
        )
    except Exception:
        pass
