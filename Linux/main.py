import time
import threading
import os
import json
import subprocess
import signal
from pypresence import Presence

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "client_id": "1482692658504794289",
    "update_interval": 15,
    "reconnect_delay": 30,
    "show_window_title": True,
    "clear_on_idle": True,
    "custom_mappings": {
        "code":          {"name": "Visual Studio Code", "icon": "vscode",    "detail": "Coding"},
        "chrome":        {"name": "Google Chrome",      "icon": "chrome",    "detail": "Browsing"},
        "firefox":       {"name": "Firefox",            "icon": "firefox",   "detail": "Browsing"},
        "discord":       {"name": "Discord",            "icon": "discord",   "detail": "Chatting"},
        "gedit":         {"name": "Text Editor",        "icon": "notepad",   "detail": "Writing"},
        "nautilus":      {"name": "Files",              "icon": "explorer",  "detail": "Browsing files"},
        "gimp":          {"name": "GIMP",               "icon": "gimp",      "detail": "Editing image"},
        "vlc":           {"name": "VLC Media Player",   "icon": "vlc",       "detail": "Watching video"},
        "spotify":       {"name": "Spotify",            "icon": "spotify",   "detail": "Listening to music"},
        "steam":         {"name": "Steam",              "icon": "steam",     "detail": "Gaming"},
        "obs":           {"name": "OBS Studio",         "icon": "obs",       "detail": "Streaming"},
        "terminal":      {"name": "Terminal",           "icon": "terminal",  "detail": "In terminal"},
        "gnome-terminal":{"name": "Terminal",           "icon": "terminal",  "detail": "In terminal"},
        "konsole":       {"name": "Terminal",           "icon": "terminal",  "detail": "In terminal"},
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


# ── Window detection (Linux) ──────────────────────────────────────────────────

def _run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def get_active_window_info():
    """
    Returns (process_name, window_title).
    Supports: xdotool (X11), ydotool fallback, wmctrl.
    """
    try:
        # X11: dùng xdotool
        win_id = _run(["xdotool", "getactivewindow"])
        if win_id:
            title = _run(["xdotool", "getwindowname", win_id])
            pid   = _run(["xdotool", "getwindowpid", win_id])
            if pid:
                proc_name = _run(["cat", f"/proc/{pid}/comm"])
                return proc_name.lower(), title
    except Exception:
        pass

    try:
        # Wayland fallback: dùng wmctrl
        lines = _run(["wmctrl", "-l"]).splitlines()
        # wmctrl không cho PID dễ, lấy active window bằng cách khác
        active = _run(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
        win_id = active.split()[-1] if active else ""
        if win_id and win_id != "0x0":
            title = _run(["xdotool", "getwindowname", str(int(win_id, 16))])
            return "unknown", title
    except Exception:
        pass

    return None, None


# ── Tray icon (AppIndicator / pystray) ───────────────────────────────────────

def _make_tray(mgr):
    """
    Try AppIndicator3 (GNOME) first, fall back to pystray.
    """
    try:
        import gi
        gi.require_version("AppIndicator3", "0.1")
        gi.require_version("Gtk", "3.0")
        from gi.repository import AppIndicator3, Gtk

        def build_menu():
            menu = Gtk.Menu()

            def add_item(label_fn, callback):
                item = Gtk.MenuItem(label=label_fn() if callable(label_fn) else label_fn)
                item._label_fn = label_fn if callable(label_fn) else None
                item.connect("activate", callback)
                menu.append(item)
                return item

            rpc_item  = add_item(lambda: "Disable RPC" if mgr.running else "Enable RPC",
                                 lambda _: (mgr.stop() if mgr.running else mgr.start()) or _refresh_menu())
            lock_item = add_item(lambda: f"Unlock ({mgr.locked_proc or '?'})" if mgr.locked else "Lock current app",
                                 lambda _: (mgr.toggle_lock()) or _refresh_menu())
            menu.append(Gtk.SeparatorMenuItem())
            add_item("Reload config", lambda _: mgr.reload_config())
            add_item("Open config.json", lambda _: subprocess.Popen(["xdg-open", CONFIG_FILE]))
            menu.append(Gtk.SeparatorMenuItem())
            add_item("Quit", lambda _: (mgr.stop(), indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE), Gtk.main_quit()))
            menu.show_all()
            return menu

        def _refresh_menu():
            indicator.set_menu(build_menu())

        indicator = AppIndicator3.Indicator.new(
            "discord-rpc",
            "dialog-information",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        indicator.set_menu(build_menu())

        mgr.start()
        Gtk.main()

    except Exception:
        # Fallback: pystray
        _make_tray_pystray(mgr)


def _make_tray_pystray(mgr):
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw

    def make_icon(locked=False):
        img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = (231, 76, 60) if locked else (88, 101, 242)
        draw.ellipse([4, 4, 60, 60], fill=color)
        draw.ellipse([24, 24, 40, 40], fill=(255, 255, 255))
        return img

    icon_ref = [None]

    def refresh_icon():
        if icon_ref[0]:
            icon_ref[0].icon  = make_icon(locked=mgr.locked)
            icon_ref[0].title = "Discord RPC [LOCKED]" if mgr.locked else "Discord RPC Watcher"

    def on_toggle_rpc(icon, item):
        if mgr.running: mgr.stop()
        else: mgr.start()

    def on_toggle_lock(icon, item):
        mgr.toggle_lock()
        refresh_icon()

    def on_reload(icon, item):
        mgr.reload_config()

    def on_open_config(icon, item):
        subprocess.Popen(["xdg-open", CONFIG_FILE])

    def on_quit(icon, item):
        mgr.stop()
        icon.stop()

    def rpc_label(item):
        return "Disable RPC" if mgr.running else "Enable RPC"

    def lock_label(item):
        if mgr.locked:
            return f"Unlock ({(mgr.locked_proc or '?')})"
        return "Lock current app"

    menu = Menu(
        MenuItem(rpc_label,       on_toggle_rpc),
        MenuItem(lock_label,      on_toggle_lock),
        Menu.SEPARATOR,
        MenuItem("Reload config", on_reload),
        MenuItem("Open config",   on_open_config),
        Menu.SEPARATOR,
        MenuItem("Quit",          on_quit),
    )

    tray = Icon("Discord RPC", make_icon(), "Discord RPC Watcher", menu)
    icon_ref[0] = tray
    mgr.start()
    tray.run()


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
        self.last_state = None
        print("[CFG] Config reloaded.")

    def connect(self):
        client_id = self.config["client_id"]
        if client_id == "YOUR_CLIENT_ID_HERE":
            print("[!] Client ID not set! Edit config.json.")
            return False
        try:
            self.rpc = Presence(client_id)
            self.rpc.connect()
            self.connected = True
            self._last_reconnect = 0
            print("[OK] Discord RPC connected!")
            return True
        except Exception as e:
            print(f"[!!] Connection failed: {e}")
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
        mapping  = mappings.get(proc_name)

        if mapping:
            app_name = mapping.get("name", proc_name)
            detail   = mapping.get("detail", f"Using {app_name}")
            icon_key = mapping.get("icon")
        else:
            app_name = proc_name
            detail   = f"Using {proc_name}"
            icon_key = None

        state    = window_title[:128] if self.config.get("show_window_title") and window_title else None
        start_ts = elapsed_since if elapsed_since else self.start_time

        presence = {
            "details":    detail,
            "state":      state,
            "start":      start_ts,
            "small_text": "[LOCKED]" if self.locked else "Active",
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

            if not proc_name:
                if self.config.get("clear_on_idle") and not self.presence_cleared:
                    try:
                        self.rpc.clear()
                        self.presence_cleared = True
                        self.last_state = None
                        print("[--] Idle: presence cleared.")
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
            print(f"[!!] Update error: {e}")
            self.connected = False
            self._last_reconnect = time.time()

    def _loop(self):
        interval = self.config.get("update_interval", 15)
        while self.running:
            if not self.connected:
                if self._should_reconnect():
                    print("[~] Reconnecting...")
                    self.connect()
                else:
                    remaining = int(self.config.get("reconnect_delay", 30) - (time.time() - self._last_reconnect))
                    print(f"[~] Waiting {remaining}s before reconnect...")
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


# ── Entry ─────────────────────────────────────────────────────────────────────

def main():
    mgr = RPCManager()

    # Graceful shutdown on Ctrl+C hoặc SIGTERM
    def handle_signal(sig, frame):
        print("\n[--] Shutting down...")
        mgr.stop()
        os._exit(0)

    signal.signal(signal.SIGINT,  handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    _make_tray(mgr)


if __name__ == "__main__":
    main()
