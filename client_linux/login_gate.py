"""
Bench Usage Automation - Linux Login Gate
Mandatory login form that blocks usage until user enters Short ID and Purpose.
Uses a centered window instead of fullscreen for smooth rendering over NoMachine.
"""

import tkinter as tk
from tkinter import ttk
import configparser
import os
import sys
import json
import logging
import subprocess
import threading
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")
LOCAL_LOG = os.path.join(SCRIPT_DIR, "local_checkins.json")
LOCK_FILE = os.path.join(SCRIPT_DIR, ".login_gate.lock")
LOGO_PATH = os.path.join(SCRIPT_DIR, "MBRDI.png")

logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "login_gate.log"),
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


def detect_access_method():
    try:
        nx_env = os.environ.get("NXSESSIONID", "")
        if nx_env:
            return "nomachine"
        result = subprocess.run(
            ["who", "-m"], capture_output=True, text=True, timeout=5
        )
        if result.stdout and "(:0)" not in result.stdout:
            return "nomachine"
    except Exception:
        pass
    return "physical"


NO_PROXY = {"http": None, "https": None}


def send_checkin(server_url, timeout, payload):
    if requests is None:
        logging.warning("requests library not available, saving locally")
        return False
    try:
        resp = requests.post(f"{server_url}/api/checkin", json=payload, timeout=timeout, proxies=NO_PROXY)
        if resp.status_code == 200:
            logging.info(f"Check-in successful: {payload['short_id']} on Bench {payload['bench_id']}")
            return True
        else:
            logging.error(f"Check-in failed ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logging.error(f"Server unreachable: {e}")
        return False


def save_local(payload):
    entries = []
    if os.path.exists(LOCAL_LOG):
        with open(LOCAL_LOG, "r") as f:
            try:
                entries = json.load(f)
            except json.JSONDecodeError:
                entries = []
    entries.append({**payload, "timestamp": datetime.now().isoformat(), "synced": False})
    with open(LOCAL_LOG, "w") as f:
        json.dump(entries, f, indent=2)
    logging.info(f"Saved check-in locally for {payload['short_id']}")


BENCH_NAMES = {1: "VIJAYANAGARA", 2: "MAURYA", 3: "CHOLA", 4: "MAGADHA", 5: "PALLAVA"}


class LoginGateApp:
    BG = "#0a0a0a"
    BG_CARD = "#161616"
    BG_INPUT = "#111111"
    BORDER = "#2a2a2a"
    TEXT = "#ffffff"
    TEXT_MUTED = "#888888"
    SILVER = "#d0d0d0"
    GREEN = "#00e676"
    RED = "#ff1744"
    BLUE = "#40c4ff"
    AMBER = "#ffd740"

    def __init__(self):
        self.config = load_config()
        self.access_method = detect_access_method()
        self.root = tk.Tk()
        self.setup_window()
        self.build_ui()

    def setup_window(self):
        self.root.title("System Function Bench Tracker | MBRDI")
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self.block_close)
        self.root.bind("<Alt-F4>", lambda e: "break")
        self.root.bind("<Escape>", lambda e: "break")
        self.root.resizable(False, False)

        win_w, win_h = 500, 550
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.attributes("-type", "dialog")

    def block_close(self):
        pass

    def build_ui(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        bench_name = BENCH_NAMES.get(self.config["bench_id"], f"BENCH {self.config['bench_id']}")

        self._logo_img = None
        if os.path.exists(LOGO_PATH):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PATH).resize((36, 36), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
            except ImportError:
                try:
                    self._logo_img = tk.PhotoImage(file=LOGO_PATH).subsample(22, 22)
                except Exception:
                    pass

        header = tk.Frame(outer, bg=self.BG)
        header.pack(pady=(0, 2))

        if self._logo_img:
            tk.Label(header, image=self._logo_img, bg=self.BG).pack(side="left", padx=(0, 12))

        title_frame = tk.Frame(header, bg=self.BG)
        title_frame.pack(side="left")
        tk.Label(title_frame, text="SYSTEM FUNCTION BENCH TRACKER", font=("Ubuntu", 14), fg=self.SILVER, bg=self.BG, anchor="w").pack(anchor="w")
        tk.Label(title_frame, text="Mercedes-Benz Research & Development India", font=("Ubuntu", 7), fg=self.TEXT_MUTED, bg=self.BG, anchor="w").pack(anchor="w")

        sep = tk.Frame(outer, bg=self.BORDER, height=1, width=400)
        sep.pack(pady=(0, 10))

        tk.Label(outer, text=bench_name, font=("Ubuntu", 20, "bold"), fg=self.TEXT, bg=self.BG).pack(pady=(0, 2))

        info_frame = tk.Frame(outer, bg=self.BG)
        info_frame.pack(pady=(0, 12))
        tk.Label(info_frame, text="LINUX PC", font=("Ubuntu", 8), fg=self.AMBER, bg=self.BG).pack(side="left", padx=(0, 10))
        tk.Label(info_frame, text=self.access_method.upper(), font=("Ubuntu", 8), fg=self.BLUE, bg=self.BG).pack(side="left")

        card = tk.Frame(outer, bg=self.BG_CARD, padx=30, pady=20, highlightbackground=self.BORDER, highlightthickness=1)
        card.pack()

        tk.Label(card, text="SHORT ID", font=("Ubuntu", 9), fg=self.SILVER, bg=self.BG_CARD, anchor="w").pack(fill="x", pady=(0, 3))

        self.short_id_var = tk.StringVar()
        self.short_id_entry = tk.Entry(
            card, textvariable=self.short_id_var, font=("Ubuntu", 13), width=28,
            bg=self.BG_INPUT, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=0,
            highlightbackground=self.BORDER, highlightthickness=1, highlightcolor="#3a3a3a",
        )
        self.short_id_entry.pack(ipady=6, pady=(0, 10))

        tk.Label(card, text="PURPOSE OF USE", font=("Ubuntu", 9), fg=self.SILVER, bg=self.BG_CARD, anchor="w").pack(fill="x", pady=(0, 3))

        self.purpose_var = tk.StringVar()
        purposes = [
            "ECU Flashing", "Diagnostic Testing", "CAN Communication",
            "Software Debug", "Calibration", "HIL Testing", "Log Collection", "Other",
        ]

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox", fieldbackground=self.BG_INPUT, background=self.BG_INPUT,
            foreground=self.TEXT, bordercolor=self.BORDER, arrowcolor=self.SILVER,
            selectbackground=self.BG_INPUT, selectforeground=self.TEXT,
            arrowsize=18, padding=(6, 4))
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", self.BG_INPUT), ("focus", self.BG_INPUT)],
            background=[("readonly", self.BG_INPUT), ("active", "#1c1c1c")],
            foreground=[("readonly", self.TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", self.BG_INPUT)
        self.root.option_add("*TCombobox*Listbox.foreground", self.TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#2a2a2a")
        self.root.option_add("*TCombobox*Listbox.selectForeground", self.TEXT)
        self.root.option_add("*TCombobox*Listbox.font", ("Ubuntu", 10))

        self.purpose_combo = ttk.Combobox(card, textvariable=self.purpose_var, values=purposes,
            font=("Ubuntu", 13), width=26, state="normal", style="Dark.TCombobox")
        self.purpose_combo.pack(ipady=6, pady=(0, 4))

        tk.Label(card, text="Or type your own purpose", font=("Ubuntu", 7), fg=self.TEXT_MUTED, bg=self.BG_CARD).pack(pady=(0, 10))

        self.error_var = tk.StringVar()
        tk.Label(card, textvariable=self.error_var, font=("Ubuntu", 9), fg=self.RED, bg=self.BG_CARD).pack(pady=(0, 6))

        self.submit_btn = tk.Button(card, text="CHECK IN & START", font=("Ubuntu", 11, "bold"),
            bg=self.GREEN, fg="#0a0a0a", activebackground="#00c853", activeforeground="#0a0a0a",
            relief="flat", cursor="hand2", command=self.submit, width=22)
        self.submit_btn.pack(ipady=8, pady=(0, 5))

        self.short_id_entry.bind("<Return>", lambda e: self.purpose_combo.focus_set())
        self.purpose_combo.bind("<Return>", lambda e: self.submit())

    def submit(self):
        if getattr(self, "_submitting", False):
            return
        self._submitting = True

        short_id = self.short_id_var.get().strip()
        purpose = self.purpose_var.get().strip()

        if not short_id:
            self.error_var.set("Please enter your Short ID")
            self.short_id_entry.focus_set()
            self._submitting = False
            return
        if not purpose:
            self.error_var.set("Please select or enter a purpose")
            self.purpose_combo.focus_set()
            self._submitting = False
            return

        self.error_var.set("")
        self.submit_btn.config(state="disabled", text="Checking in...")
        self.root.update_idletasks()

        payload = {
            "bench_id": self.config["bench_id"],
            "pc_type": self.config["pc_type"],
            "short_id": short_id.upper(),
            "purpose": purpose,
            "access_method": self.access_method,
        }

        self.root.after(50, lambda: self._do_checkin(payload))

    def _do_checkin(self, payload):
        def _worker():
            success = send_checkin(self.config["server_url"], self.config["timeout"], payload)
            if not success:
                save_local(payload)
                self.root.after(0, lambda: self.error_var.set("Server offline - logged locally. You may proceed."))
            self.root.after(300, self.close_gate)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def close_gate(self):
        logging.info("Login gate closing - user checked in")
        self.root.destroy()

    def _force_focus(self):
        self.root.focus_force()
        self.short_id_entry.focus_set()

    def _keep_on_top(self):
        try:
            self.root.lift()
        except Exception:
            return
        self.root.after(3000, self._keep_on_top)

    def run(self):
        self.root.after(300, self._force_focus)
        self.root.after(3000, self._keep_on_top)
        self.root.mainloop()


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if os.path.exists(f"/proc/{pid}"):
                logging.info(f"Another login gate is already running (PID {pid}), exiting")
                return False
        except (ValueError, Exception):
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    try:
        os.remove(LOCK_FILE)
    except Exception:
        pass


if __name__ == "__main__":
    logging.info("Login gate started")
    if not acquire_lock():
        sys.exit(0)
    try:
        app = LoginGateApp()
        app.run()
    finally:
        release_lock()
