import time
import threading
import sys
import os
import json
import ctypes
import win32gui
import win32process
import psutil
from pypresence import Presence
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "client_id": "YOUR_CLIENT_ID_HERE",
    "update_interval": 15,
    "reconnect_delay": 30,
    "show_window_title": True,
    "clear_on_idle": True,
    "custom_mappings": {
        "Code.exe":      {"name": "Visual Studio Code", "icon": "vscode",    "detail": "Dang code"},
        "chrome.exe":    {"name": "Google Chrome",      "icon": "chrome",    "detail": "Dang luot web"},
        "firefox.exe":   {"name": "Firefox",            "icon": "firefox",   "detail": "Dang luot web"},
        "discord.exe":   {"name": "Discord",            "icon": "discord",   "detail": "Dang chat"},
        "notepad.exe":   {"name": "Notepad",            "icon": "notepad",   "detail": "Dang viet"},
        "explorer.exe":  {"name": "File Explorer",      "icon": "explorer",  "detail": "Dang xem file"},
        "Photoshop.exe": {"name": "Adobe Photoshop",    "icon": "photoshop", "detail": "Dang edit anh"},
        "vlc.exe":       {"name": "VLC Media Player",   "icon": "vlc",       "detail": "Dang xem video"},
        "spotify.exe":   {"name": "Spotify",            "icon": "spotify",   "detail": "Dang nghe nhac"},
        "steam.exe":     {"name": "Steam",              "icon": "steam",     "detail": "Dang choi game"},
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── Window detection ──────────────────────────────────────────────────────────

def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name(), title
    except Exception:
        return None, None


# ── RPC Manager ───────────────────────────────────────────────────────────────

class RPCManager:
    def __init__(self):
        self.config = load_config()
        self.rpc = None
        self.connected = False
        self.running = False
        self.start_time = int(time.time())
        self.last_state = None
        self.presence_cleared = False
        self._thread = None
        self._last_reconnect = 0

        self.locked = False
        self.locked_proc = None
        self.locked_title = None
        self.locked_since = None

    def reload_config(self):
        self.config = load_config()
        self.last_state = None  # force update với config mới
        print("[CFG] Config da duoc reload.")

    def connect(self):
        client_id = self.config["client_id"]
        if client_id == "YOUR_CLIENT_ID_HERE":
            print("[!] Chua set Client ID! Mo config.json va dien vao.")
            return False
        try:
            self.rpc = Presence(client_id)
            self.rpc.connect()
            self.connected = True
            self._last_reconnect = 0
            print("[OK] Da ket noi Discord RPC!")
            return True
        except Exception as e:
            print(f"[!!] Khong ket noi duoc Discord: {e}")
            self.connected = False
            self._last_reconnect = time.time()
            return False

    def disconnect(self):
        if self.connected and self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
        self.connected = False

    def toggle_lock(self):
        if not self.locked:
            proc, title = get_active_window_info()
            if proc:
                self.locked = True
                self.locked_proc = proc
                self.locked_title = title
                self.locked_since = int(time.time())
                self.last_state = None
                print(f"[LOCK] Locked: {proc}")
        else:
            self.locked = False
            self.locked_proc = None
            self.locked_title = None
            self.locked_since = None
            self.last_state = None
            print("[LOCK] Unlocked.")

    def _build_presence(self, proc_name, window_title, elapsed_since=None):
        mappings = self.config.get("custom_mappings", {})
        mapping = mappings.get(proc_name)

        if mapping:
            app_name = mapping.get("name", proc_name)
            detail   = mapping.get("detail", f"Dang dung {app_name}")
            icon_key = mapping.get("icon")
        else:
            clean    = proc_name.replace(".exe", "")
            app_name = clean
            detail   = f"Dang dung {clean}"
            icon_key = None

        state = window_title[:128] if self.config.get("show_window_title") and window_title else None
        start_ts = elapsed_since if elapsed_since else self.start_time

        presence = {
            "details": detail,
            "state":   state,
            "start":   start_ts,
            "small_text": "[LOCKED]" if self.locked else "Dang hoat dong",
        }
        if icon_key:
            presence["large_image"] = icon_key
            presence["large_text"]  = app_name

        return presence

    def _should_reconnect(self):
        delay = self.config.get("reconnect_delay", 30)
        return time.time() - self._last_reconnect >= delay

    def update_once(self):
        if not self.connected:
            return

        if self.locked and self.locked_proc:
            proc_name    = self.locked_proc
            window_title = self.locked_title
            since        = self.locked_since
        else:
            proc_name, window_title = get_active_window_info()
            since = None

            # Idle detection — không có window active thì clear presence
            if not proc_name:
                if not self.presence_cleared:
                    try:
                        self.rpc.clear()
                        self.presence_cleared = True
                        self.last_state = None
                        print("[--] Idle: cleared presence.")
                    except Exception:
                        self.connected = False
                return

        self.presence_cleared = False
        presence  = self._build_presence(proc_name, window_title, elapsed_since=since)
        state_key = (proc_name, window_title, self.locked)

        if state_key == self.last_state:
            return

        try:
            self.rpc.update(**presence)
            self.last_state = state_key
            lock_tag = " [LOCKED]" if self.locked else ""
            print(f"[UP]{lock_tag} {proc_name} -- {(window_title or '')[:50]}")
        except Exception as e:
            print(f"[!!] Update loi: {e}")
            self.connected = False
            self._last_reconnect = time.time()

    def _loop(self):
        interval = self.config.get("update_interval", 15)
        while self.running:
            if not self.connected:
                if self._should_reconnect():
                    print("[~] Dang thu ket noi lai...")
                    self.connect()
                else:
                    remaining = int(self.config.get("reconnect_delay", 30) - (time.time() - self._last_reconnect))
                    print(f"[~] Cho {remaining}s truoc khi ket noi lai...")
            else:
                self.update_once()
            time.sleep(interval)

    def start(self):
        if self.running:
            return
        if not self.connect():
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self.disconnect()


# ── Tray icon ─────────────────────────────────────────────────────────────────

def make_icon(locked=False):
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (231, 76, 60) if locked else (88, 101, 242)
    draw.ellipse([4, 4, 60, 60], fill=color)
    draw.ellipse([24, 24, 40, 40], fill=(255, 255, 255))
    return img


def run_tray(mgr):
    icon_ref = [None]

    def refresh_icon():
        if icon_ref[0]:
            icon_ref[0].icon  = make_icon(locked=mgr.locked)
            icon_ref[0].title = "Discord RPC [LOCKED]" if mgr.locked else "Discord RPC Watcher"

    def on_toggle_rpc(icon, item):
        if mgr.running:
            mgr.stop()
        else:
            mgr.start()

    def on_toggle_lock(icon, item):
        mgr.toggle_lock()
        refresh_icon()

    def on_reload_config(icon, item):
        mgr.reload_config()

    def on_open_config(icon, item):
        os.startfile(CONFIG_FILE)

    def on_quit(icon, item):
        mgr.stop()
        icon.stop()

    def rpc_label(item):
        return "Tat RPC" if mgr.running else "Bat RPC"

    def lock_label(item):
        if mgr.locked:
            proc = mgr.locked_proc or "?"
            return f"Mo khoa ({proc.replace('.exe', '')})"
        return "Khoa app hien tai"

    menu = Menu(
        MenuItem(rpc_label,          on_toggle_rpc),
        MenuItem(lock_label,         on_toggle_lock),
        Menu.SEPARATOR,
        MenuItem("Reload config",    on_reload_config),
        MenuItem("Mo config.json",   on_open_config),
        Menu.SEPARATOR,
        MenuItem("Thoat",            on_quit),
    )

    tray = Icon("Discord RPC", make_icon(), "Discord RPC Watcher", menu)
    icon_ref[0] = tray
    mgr.start()
    tray.run()


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0
        )
    mgr = RPCManager()
    run_tray(mgr)
