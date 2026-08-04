"""
Bench Usage Automation - Linux Session Monitor
Detects: NoMachine disconnect/reconnect, screen lock, logoff.
Sends checkout on disconnect, launches login gate on reconnect.

Detection methods:
1. NoMachine log file monitoring (/usr/NX/var/log/nxserver.log)
2. `who` command to check active user sessions
3. loginctl for screen lock detection
"""

import configparser
import os
import sys
import time
import logging
import subprocess
import glob

try:
    import requests
except ImportError:
    requests = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")
LOGIN_GATE_PATH = os.path.join(SCRIPT_DIR, "login_gate.py")
VENV_PYTHON = os.path.join(SCRIPT_DIR, "venv", "bin", "python")

_last_checkout_time = 0
_last_gate_time = 0

logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "session_monitor.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    return {
        "server_url": config.get("server", "url", fallback="http://localhost:8000"),
        "timeout": config.getint("server", "timeout", fallback=10),
        "bench_id": config.getint("bench", "bench_id", fallback=1),
        "pc_type": config.get("bench", "pc_type", fallback="linux"),
    }


NO_PROXY = {"http": None, "https": None}


def send_checkout(config):
    global _last_checkout_time
    now = time.time()
    if now - _last_checkout_time < 10:
        logging.info("Skipping checkout — already sent recently")
        return True
    _last_checkout_time = now

    if requests is None:
        logging.error("requests library not available")
        return False

    payload = {
        "bench_id": config["bench_id"],
        "pc_type": config["pc_type"],
    }
    try:
        resp = requests.post(
            f"{config['server_url']}/api/checkout",
            json=payload,
            timeout=config["timeout"],
            proxies=NO_PROXY,
        )
        if resp.status_code in (200, 404):
            logging.info(f"Checkout successful for Bench {config['bench_id']}")
            return True
        else:
            logging.warning(f"Checkout failed: {resp.status_code}")
            return False
    except Exception as e:
        logging.warning(f"Checkout error: {e}")
        return False


def get_active_user():
    """Find the currently logged-in desktop user."""
    try:
        result = subprocess.run(["who"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                return line.split()[0]
    except Exception:
        pass
    return None


def get_user_display(username):
    """Find the DISPLAY and XAUTHORITY for a logged-in user."""
    display = ":0"
    xauth = ""

    try:
        result = subprocess.run(["who"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.strip().split("\n"):
            if username in line and "(" in line:
                disp = line.split("(")[-1].rstrip(")")
                if disp.startswith(":"):
                    display = disp
                    break
    except Exception:
        pass

    home_dir = f"/home/{username}"
    xa = os.path.join(home_dir, ".Xauthority")
    if os.path.exists(xa):
        xauth = xa

    return display, xauth


def launch_login_gate():
    global _last_gate_time
    now = time.time()
    if now - _last_gate_time < 10:
        logging.info("Skipping login gate launch — already launched recently")
        return
    _last_gate_time = now

    python_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    if not os.path.exists(LOGIN_GATE_PATH):
        logging.warning(f"Login gate not found at {LOGIN_GATE_PATH}")
        return

    username = get_active_user()
    if not username:
        logging.warning("No active user found — cannot launch login gate")
        return

    display, xauth = get_user_display(username)
    logging.info(f"Launching login gate as {username} on display {display}")

    try:
        cmd = [
            "su", "-", username, "-c",
            f"DISPLAY={display} XAUTHORITY={xauth} {python_exe} {LOGIN_GATE_PATH}"
        ]
        subprocess.Popen(cmd)
    except Exception as e:
        logging.error(f"Failed to launch login gate: {e}")


def count_remote_sessions():
    """Count active remote sessions using `who`, ignoring physical console (tty)."""
    try:
        result = subprocess.run(
            ["who"], capture_output=True, text=True, timeout=5,
        )
        count = 0
        for line in result.stdout.strip().split("\n"):
            if line.strip() and "tty" not in line.split()[1]:
                count += 1
        return count
    except Exception:
        return -1


def check_nomachine_connected():
    """Check if any NoMachine client is connected by looking for TCP connections on port 4000."""
    try:
        result = subprocess.run(
            ["ss", "-tn"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            if ":4000" in line and "ESTAB" in line:
                return True
        return False
    except Exception as e:
        logging.debug(f"NoMachine connection check error: {e}")
        return None


def is_screen_locked():
    """Detect screen lock via loginctl or dbus."""
    try:
        result = subprocess.run(
            ["loginctl", "show-session", "auto", "-p", "LockedHint"],
            capture_output=True, text=True, timeout=5,
        )
        if "LockedHint=yes" in result.stdout:
            return True
        if "LockedHint=no" in result.stdout:
            return False
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["dbus-send", "--session", "--dest=org.gnome.ScreenSaver",
             "--type=method_call", "--print-reply",
             "/org/gnome/ScreenSaver", "org.gnome.ScreenSaver.GetActive"],
            capture_output=True, text=True, timeout=5,
        )
        if "boolean true" in result.stdout.lower():
            return True
        if "boolean false" in result.stdout.lower():
            return False
    except Exception:
        pass

    return None


def monitor_loop(config):
    logging.info("Starting session monitor loop")
    was_active = False

    while True:
        try:
            nx_connected = check_nomachine_connected()
            locked = is_screen_locked()

            is_active = nx_connected is True

            if locked is True:
                is_active = False

            if is_active and not was_active:
                logging.info("NoMachine connected — launching login gate")
                launch_login_gate()
                was_active = True
            elif not is_active and was_active:
                reason = "screen lock" if locked else "NoMachine disconnected"
                logging.info(f"Release triggered ({reason}) — sending checkout")
                send_checkout(config)
                was_active = False

        except Exception as e:
            logging.error(f"Monitor loop error: {e}")

        time.sleep(10)


if __name__ == "__main__":
    config = load_config()
    logging.info(f"Session monitor started for Bench {config['bench_id']} ({config['pc_type']})")
    monitor_loop(config)
