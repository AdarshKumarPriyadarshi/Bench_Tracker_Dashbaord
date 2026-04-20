"""
Bench Usage Automation - Windows Session Monitor
Detects: RDP disconnect, logoff, screen lock (Win+L), and physical session end.
Sends checkout to server to auto-release the bench.
On session resume (unlock/reconnect), launches the login gate.

Uses a hybrid approach: WTS event-based monitoring as primary,
with a polling safety net thread that catches events missed by the message pump.
"""

import configparser
import os
import sys
import time
import logging
import subprocess
import threading
import ctypes
import ctypes.wintypes

try:
    import requests
except ImportError:
    requests = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")
LOGIN_GATE_PATH = os.path.join(SCRIPT_DIR, "login_gate.py")
VENV_PYTHON = os.path.join(SCRIPT_DIR, "..", "venv", "Scripts", "python.exe")

_last_gate_time = 0
_last_checkout_time = 0
_session_active = True

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
        "pc_type": config.get("bench", "pc_type", fallback="windows"),
    }


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


def launch_login_gate():
    global _last_gate_time
    now = time.time()
    if now - _last_gate_time < 10:
        logging.info("Skipping login gate launch — already launched recently")
        return
    _last_gate_time = now

    python_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    if os.path.exists(LOGIN_GATE_PATH):
        logging.info(f"Launching login gate: {LOGIN_GATE_PATH}")
        try:
            subprocess.Popen([python_exe, LOGIN_GATE_PATH])
        except Exception as e:
            logging.error(f"Failed to launch login gate: {e}")
    else:
        logging.warning(f"Login gate not found at {LOGIN_GATE_PATH}")


def send_heartbeat(config):
    if requests is None:
        return
    try:
        requests.get(f"{config['server_url']}/api/health", timeout=5)
    except Exception:
        pass


def is_screen_locked():
    """Detect if the workstation is locked using OpenInputDesktop."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x0100)
        if hdesk == 0:
            return True
        user32.CloseDesktop(hdesk)
        return False
    except Exception:
        return False


def is_session_disconnected():
    """Check if current process's session is disconnected using WTS query."""
    try:
        import win32ts
        my_session = win32ts.ProcessIdToSessionId(os.getpid())
        sessions = win32ts.WTSEnumerateSessions(win32ts.WTS_CURRENT_SERVER_HANDLE)
        for sess in sessions:
            if sess["SessionId"] == my_session:
                return sess["State"] == 4  # WTSDisconnected
        return None
    except Exception as e:
        logging.debug(f"Session state check failed: {e}")
        return None


def safety_net_poller(config):
    """
    Background thread that polls session state every 15 seconds.
    Catches disconnect/reconnect events that the WTS message pump might miss.
    """
    global _session_active
    logging.info("Safety-net poller started")

    time.sleep(5)

    while True:
        try:
            disconnected = is_session_disconnected()
            if disconnected is None:
                time.sleep(15)
                continue

            if disconnected and _session_active:
                logging.info("Safety-net: session disconnected detected via polling")
                _session_active = False
                send_checkout(config)
            elif not disconnected and not _session_active:
                logging.info("Safety-net: session reconnected detected via polling")
                _session_active = True
                launch_login_gate()

        except Exception as e:
            logging.error(f"Safety-net poller error: {e}")

        time.sleep(15)


def monitor_with_wts_events(config):
    """
    Event-based monitor using Windows Terminal Services notifications.
    Detects: lock, unlock, disconnect, logoff.
    Also starts a safety-net polling thread for reliability.
    """
    global _session_active
    import win32ts
    import win32gui
    import win32api

    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_CONSOLE_CONNECT = 0x1
    WTS_CONSOLE_DISCONNECT = 0x2
    WTS_REMOTE_CONNECT = 0x3
    WTS_REMOTE_DISCONNECT = 0x4
    WTS_SESSION_LOGON = 0x5
    WTS_SESSION_LOGOFF = 0x6
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8
    NOTIFY_FOR_ALL_SESSIONS = 1

    RELEASE_EVENTS = (WTS_SESSION_LOCK, WTS_SESSION_LOGOFF, WTS_CONSOLE_DISCONNECT, WTS_REMOTE_DISCONNECT)
    RESUME_EVENTS = (WTS_SESSION_UNLOCK, WTS_CONSOLE_CONNECT, WTS_REMOTE_CONNECT, WTS_SESSION_LOGON)

    EVENT_NAMES = {
        0x1: "CONSOLE_CONNECT",
        0x2: "CONSOLE_DISCONNECT",
        0x3: "REMOTE_CONNECT (RDP)",
        0x4: "REMOTE_DISCONNECT (RDP)",
        0x5: "SESSION_LOGON",
        0x6: "SESSION_LOGOFF",
        0x7: "SESSION_LOCK (Win+L)",
        0x8: "SESSION_UNLOCK",
    }

    def wnd_proc(hwnd, msg, wparam, lparam):
        global _session_active
        if msg == WM_WTSSESSION_CHANGE:
            event_name = EVENT_NAMES.get(lparam, f"UNKNOWN({lparam})")
            if lparam in RELEASE_EVENTS:
                logging.info(f"Release event: {event_name}")
                _session_active = False
                send_checkout(config)
            elif lparam in RESUME_EVENTS:
                logging.info(f"Resume event: {event_name} — launching login gate")
                _session_active = True
                launch_login_gate()
            else:
                logging.info(f"Session event (no action): {event_name}")
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = wnd_proc
    wc.lpszClassName = "BenchSessionMonitor"
    wc.hInstance = win32api.GetModuleHandle(None)
    class_atom = win32gui.RegisterClass(wc)

    hwnd = win32gui.CreateWindow(
        class_atom, "BenchSessionMonitor",
        0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
    )

    win32ts.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_ALL_SESSIONS)
    logging.info("WTS event monitor started — listening for lock/disconnect/logoff")

    poller_thread = threading.Thread(target=safety_net_poller, args=(config,), daemon=True)
    poller_thread.start()

    win32gui.PumpMessages()


def monitor_polling(config):
    """
    Fallback polling monitor (when pywin32 is not available).
    Checks screen lock state every 10 seconds.
    """
    logging.info("Starting polling-based session monitor")
    was_active = True

    while True:
        try:
            locked = is_screen_locked()

            if locked and was_active:
                logging.info("Screen locked — triggering checkout")
                send_checkout(config)
                was_active = False

            elif not locked and not was_active:
                logging.info("Screen unlocked — launching login gate")
                launch_login_gate()
                was_active = True

            send_heartbeat(config)
        except Exception as e:
            logging.error(f"Monitor loop error: {e}")

        time.sleep(10)


if __name__ == "__main__":
    config = load_config()
    logging.info(f"Session monitor started for Bench {config['bench_id']} ({config['pc_type']})")

    try:
        import win32ts
        import win32gui
        import win32api
        logging.info("pywin32 available — using WTS event-based monitoring")
        monitor_with_wts_events(config)
    except ImportError:
        logging.info("pywin32 not available — using polling-based monitoring")
        monitor_polling(config)
