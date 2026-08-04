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
VENV_PYTHON = os.path.join(SCRIPT_DIR, "venv", "Scripts", "python.exe")

_last_gate_time = 0
_last_checkout_time = 0
_last_wts_event_time = 0
_last_lock_time = 0
_session_active = True

logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "session_monitor.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

NO_PROXY = {"http": None, "https": None}


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
        logging.info("Skipping checkout - already sent recently")
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


def is_login_gate_running():
    lock_file = os.path.join(SCRIPT_DIR, ".login_gate.lock")
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r") as f:
                pid = int(f.read().strip())
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
        except (ValueError, Exception):
            pass
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "name='pythonw.exe'", "get", "commandline"],
            capture_output=True, text=True, timeout=5
        )
        if "login_gate" in result.stdout.lower():
            return True
    except Exception:
        pass
    return False


def launch_login_gate():
    global _last_gate_time
    now = time.time()
    if now - _last_gate_time < 30:
        logging.info("Skipping login gate launch - already launched recently")
        return
    if is_login_gate_running():
        logging.info("Skipping login gate launch - already running")
        _last_gate_time = now
        return
    _last_gate_time = now

    python_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    if os.path.exists(LOGIN_GATE_PATH):
        logging.info(f"Launching login gate: {LOGIN_GATE_PATH}")
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            subprocess.Popen([python_exe, LOGIN_GATE_PATH], startupinfo=startupinfo)
        except Exception as e:
            logging.error(f"Failed to launch login gate: {e}")
    else:
        logging.warning(f"Login gate not found at {LOGIN_GATE_PATH}")


def send_heartbeat(config):
    if requests is None:
        return
    try:
        requests.get(f"{config['server_url']}/api/health", timeout=5, proxies=NO_PROXY)
    except Exception:
        pass


def is_screen_locked():
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
    try:
        import win32ts
        my_session = win32ts.ProcessIdToSessionId(os.getpid())
        sessions = win32ts.WTSEnumerateSessions(win32ts.WTS_CURRENT_SERVER_HANDLE)
        for sess in sessions:
            if sess["SessionId"] == my_session:
                return sess["State"] == 4
        return None
    except Exception as e:
        logging.debug(f"Session state check failed: {e}")
        return None


def safety_net_poller(config):
    global _session_active, _last_wts_event_time
    logging.info("Safety-net poller started")

    time.sleep(10)

    while True:
        try:
            if time.time() - _last_wts_event_time < 10:
                time.sleep(5)
                continue

            disconnected = is_session_disconnected()
            if disconnected is None:
                time.sleep(5)
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

        time.sleep(5)


def delayed_disconnect_check(config):
    global _session_active
    time.sleep(5)
    disconnected = is_session_disconnected()
    if disconnected and _session_active:
        logging.info("Confirmed disconnect after 5s delay - sending checkout")
        _session_active = False
        send_checkout(config)


def monitor_with_wts_events(config):
    global _session_active, _last_wts_event_time
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

    RELEASE_EVENTS = (WTS_SESSION_LOCK, WTS_SESSION_LOGOFF, WTS_REMOTE_DISCONNECT)
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
        global _session_active, _last_wts_event_time, _last_lock_time
        if msg == WM_WTSSESSION_CHANGE:
            _last_wts_event_time = time.time()
            event_name = EVENT_NAMES.get(lparam, f"UNKNOWN({lparam})")
            if lparam in RELEASE_EVENTS:
                logging.info(f"Release event: {event_name}")
                _session_active = False
                if lparam == WTS_SESSION_LOCK:
                    _last_lock_time = time.time()
                send_checkout(config)
            elif lparam in RESUME_EVENTS:
                if time.time() - _last_lock_time < 15:
                    logging.info(f"Resume event: {event_name} - ignored (within 15s of lock)")
                else:
                    logging.info(f"Resume event: {event_name} - launching login gate")
                    _session_active = True
                    launch_login_gate()
            elif lparam == WTS_CONSOLE_DISCONNECT:
                logging.info("Console disconnect - verifying in 10s")
                threading.Thread(target=delayed_disconnect_check, args=(config,), daemon=True).start()
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
    logging.info("WTS event monitor started - listening for lock/disconnect/logoff")

    poller_thread = threading.Thread(target=safety_net_poller, args=(config,), daemon=True)
    poller_thread.start()

    win32gui.PumpMessages()


def monitor_polling(config):
    logging.info("Starting polling-based session monitor")
    was_active = True

    while True:
        try:
            locked = is_screen_locked()

            if locked and was_active:
                logging.info("Screen locked - triggering checkout")
                send_checkout(config)
                was_active = False

            elif not locked and not was_active:
                logging.info("Screen unlocked - launching login gate")
                launch_login_gate()
                was_active = True

            send_heartbeat(config)
        except Exception as e:
            logging.error(f"Monitor loop error: {e}")

        time.sleep(10)


def is_another_monitor_running():
    """Check if another session monitor is already running via lock file."""
    lock_path = os.path.join(SCRIPT_DIR, ".session_monitor.lock")
    my_pid = os.getpid()
    if os.path.exists(lock_path):
        try:
            with open(lock_path, "r") as f:
                old_pid = int(f.read().strip())
            if old_pid != my_pid:
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, old_pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
        except (ValueError, Exception):
            pass
    with open(lock_path, "w") as f:
        f.write(str(my_pid))
    return False


if __name__ == "__main__":
    if is_another_monitor_running():
        sys.exit(0)

    MAX_RESTARTS = 50
    restart_count = 0

    while restart_count < MAX_RESTARTS:
        try:
            config = load_config()
            logging.info(f"Session monitor started for Bench {config['bench_id']} ({config['pc_type']})")


            time.sleep(5)
            logging.info("Launching login gate on startup")
            launch_login_gate()

            try:
                import win32ts
                import win32gui
                import win32api
                logging.info("pywin32 available - using WTS event-based monitoring")
                monitor_with_wts_events(config)
            except ImportError:
                logging.info("pywin32 not available - using polling-based monitoring")
                monitor_polling(config)
        except Exception as e:
            restart_count += 1
            logging.error(f"Session monitor crashed: {e}. Restarting ({restart_count}/{MAX_RESTARTS})...")
            time.sleep(10)

    logging.error("Max restarts reached. Session monitor stopped.")
