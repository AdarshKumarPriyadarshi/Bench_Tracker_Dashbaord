"""
Bench Usage Automation - Windows Login Gate
Fullscreen mandatory login form that blocks desktop until user enters Short ID and Purpose.
Triggered on every Windows logon (RDP or physical).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import configparser
import os
import sys
import ctypes
import json
import logging
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
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_gate.log"),
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


def detect_access_method():
    try:
        SM_REMOTESESSION = 0x1000
        is_remote = ctypes.windll.user32.GetSystemMetrics(SM_REMOTESESSION)
        return "rdp" if is_remote else "physical"
    except Exception:
        return "physical"


def send_checkin(server_url, timeout, payload):
    if requests is None:
        logging.warning("requests library not available, saving locally")
        return False

    try:
        resp = requests.post(
            f"{server_url}/api/checkin",
            json=payload,
            timeout=timeout,
            proxies=NO_PROXY,
        )
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


class LoginGateApp:
    BG = "#0a0a0a"
    BG_CARD = "#161616"
    BG_INPUT = "#111111"
    BORDER = "#2a2a2a"
    TEXT = "#ffffff"
    TEXT_SEC = "#cccccc"
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
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self.block_close)
        self.root.bind("<Alt-F4>", lambda e: "break")
        self.root.bind("<Alt-Tab>", lambda e: "break")
        self.root.bind("<Escape>", lambda e: "break")
        self.root.overrideredirect(False)
        self.root.focus_force()
        self.root.grab_set()

    def block_close(self):
        pass

    def build_ui(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")

        self._logo_img = None
        self._logo_frames = []
        if os.path.exists(LOGO_PATH):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PATH).resize((56, 56), Image.LANCZOS)
                for angle in range(0, 360, 10):
                    rotated = img.rotate(-angle, resample=Image.BICUBIC, expand=False)
                    self._logo_frames.append(ImageTk.PhotoImage(rotated))
                self._logo_img = self._logo_frames[0]
            except ImportError:
                try:
                    self._logo_img = tk.PhotoImage(file=LOGO_PATH).subsample(8, 8)
                except Exception:
                    pass

        header = tk.Frame(outer, bg=self.BG)
        header.pack(pady=(0, 8))

        self._logo_label = None
        if self._logo_img:
            self._logo_label = tk.Label(header, image=self._logo_img, bg=self.BG)
            self._logo_label.pack(side="left", padx=(0, 8))
            if self._logo_frames:
                self._logo_frame_idx = 0
                self._rotate_logo()

        title_frame = tk.Frame(header, bg=self.BG)
        title_frame.pack(side="left")
        tk.Label(
            title_frame,
            text="SYSTEM FUNCTION BENCH TRACKER",
            font=("Segoe UI", 18),
            fg=self.SILVER,
            bg=self.BG,
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_frame,
            text="Mercedes-Benz Research & Development India",
            font=("Segoe UI", 9),
            fg=self.TEXT_MUTED,
            bg=self.BG,
            anchor="w",
        ).pack(anchor="w")

        sep = tk.Frame(outer, bg=self.BORDER, height=1)
        sep.pack(fill="x", pady=(8, 15))

        bench_names = {1: "VIJAYANAGARA", 2: "MAURYA", 3: "CHOLA", 4: "MAGADHA", 5: "PALLAVA"}
        bench_name = bench_names.get(self.config["bench_id"], f"BENCH {self.config['bench_id']}")

        tk.Label(
            outer,
            text=bench_name,
            font=("Segoe UI", 22),
            fg=self.TEXT,
            bg=self.BG,
        ).pack(pady=(0, 2))

        info_frame = tk.Frame(outer, bg=self.BG)
        info_frame.pack(pady=(0, 15))
        tk.Label(info_frame, text=f"{self.config['pc_type'].upper()} PC", font=("Segoe UI", 9), fg=self.AMBER, bg=self.BG).pack(side="left", padx=(0, 15))
        tk.Label(info_frame, text=self.access_method.upper(), font=("Segoe UI", 8), fg=self.BLUE, bg=self.BG).pack(side="left")

        card = tk.Frame(outer, bg=self.BG_CARD, padx=40, pady=25, highlightbackground=self.BORDER, highlightthickness=1)
        card.pack()

        tk.Label(card, text="IDENTIFY YOURSELF", font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg=self.BG_CARD, anchor="w").pack(fill="x", pady=(0, 12))

        tk.Label(card, text="SHORT ID", font=("Segoe UI", 8), fg=self.SILVER, bg=self.BG_CARD, anchor="w").pack(fill="x", pady=(0, 3))

        self.short_id_var = tk.StringVar()
        self.short_id_entry = tk.Entry(
            card, textvariable=self.short_id_var, font=("Segoe UI", 13),
            bg=self.BG_INPUT, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", bd=0,
            highlightbackground=self.BORDER, highlightthickness=1, highlightcolor="#3a3a3a",
        )
        self.short_id_entry.pack(ipady=8, pady=(0, 12), fill="x")
        self.short_id_entry.focus_set()

        tk.Label(card, text="PURPOSE OF USE", font=("Segoe UI", 8), fg=self.SILVER, bg=self.BG_CARD, anchor="w").pack(fill="x", pady=(0, 3))

        self.purpose_var = tk.StringVar()
        purposes = [
            "Automation Execution", "Automation Integration",
            "Bench Debugging (HW)", "Software Flashing",
            "Diagnostic (SEM) Testing", "Execution Analysis",
            "Log Collection", "Manual Execution",
            "Night Run Execution - DND", "Software Debugging",
        ]

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox", fieldbackground=self.BG_INPUT, background=self.BG_INPUT,
            foreground=self.TEXT, bordercolor=self.BORDER, arrowcolor=self.SILVER,
            selectbackground=self.BG_INPUT, selectforeground=self.TEXT,
            insertcolor=self.TEXT, arrowsize=20, padding=(8, 5))
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", self.BG_INPUT), ("focus", self.BG_INPUT)],
            background=[("readonly", self.BG_INPUT), ("active", "#1c1c1c")],
            foreground=[("readonly", self.TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", self.BG_INPUT)
        self.root.option_add("*TCombobox*Listbox.foreground", self.TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#2a2a2a")
        self.root.option_add("*TCombobox*Listbox.selectForeground", self.TEXT)
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 11))

        self.purpose_combo = ttk.Combobox(card, textvariable=self.purpose_var, values=purposes,
            font=("Segoe UI", 12), width=28, state="normal", style="Dark.TCombobox")
        self.purpose_combo.pack(ipady=7, pady=(0, 5))

        tk.Label(card, text="Or type your own purpose above", font=("Segoe UI", 7), fg=self.TEXT_MUTED, bg=self.BG_CARD).pack(pady=(0, 12))

        self.error_var = tk.StringVar()
        self.error_label = tk.Label(card, textvariable=self.error_var, font=("Segoe UI", 9), fg=self.RED, bg=self.BG_CARD)
        self.error_label.pack(pady=(0, 8))

        self.submit_btn = tk.Button(card, text="CHECK IN & START", font=("Segoe UI", 11, "bold"),
            bg="#ffffff", fg="#0a0a0a", activebackground="#e0e0e0", activeforeground="#0a0a0a",
            relief="flat", cursor="hand2", command=self.submit, width=25, height=1)
        self.submit_btn.pack(ipady=6, pady=(0, 5))

        self.short_id_entry.bind("<Return>", lambda e: self.purpose_combo.focus_set())
        self.purpose_combo.bind("<Return>", lambda e: self.submit())

    def _rotate_logo(self):
        self._logo_frame_idx = (self._logo_frame_idx + 1) % len(self._logo_frames)
        self._logo_label.config(image=self._logo_frames[self._logo_frame_idx])
        self.root.after(50, self._rotate_logo)

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
        self.submit_btn.config(state="disabled", text="Checking in...", bg=self.GREEN)
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
        self.root.grab_release()
        self.root.destroy()

    def _force_focus(self):
        self.root.focus_force()
        self.root.grab_set()
        self.short_id_entry.focus_set()

    def run(self):
        self.root.after(300, self._force_focus)
        self.root.mainloop()


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
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
