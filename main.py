import ctypes
import logging
import os
import signal
import subprocess
import sys

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from app.config import get_config_path
from app.presence import PresenceEngine

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("discord-rpc")


def make_icon(locked=False):
    """Generates a 64x64 dynamic icon. Red when locked, Blurple when active."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (231, 76, 60) if locked else (88, 101, 242)
    draw.ellipse([4, 4, 60, 60], fill=color)
    draw.ellipse([24, 24, 40, 40], fill=(255, 255, 255))
    return img


def open_file_externally(path):
    """Opens a file using the operating system's default handler."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
    except Exception as e:
        logger.warning("Could not open file %s: %s", path, e)


def run_app():
    # Hide console window on Windows when not explicitly launched in persistent terminal
    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

    engine = PresenceEngine()
    icon_ref = [None]

    def refresh_icon():
        if icon_ref[0]:
            icon_ref[0].icon = make_icon(locked=engine.locked)
            icon_ref[0].title = "Discord RPC [LOCKED]" if engine.locked else "Discord RPC Watcher"

    def on_toggle_rpc(icon, item):
        if engine.running:
            engine.stop()
        else:
            engine.start()

    def on_toggle_lock(icon, item):
        engine.toggle_lock()
        refresh_icon()

    def on_reload_config(icon, item):
        engine.reload_config()

    def on_open_config(icon, item):
        open_file_externally(get_config_path())

    def on_quit(icon, item):
        logger.info("Shutting down Discord RPC Watcher...")
        engine.stop()
        icon.stop()

    def rpc_label(item):
        return "Disable RPC" if engine.running else "Enable RPC"

    def lock_label(item):
        if engine.locked:
            proc = (engine.locked_proc or "?").replace(".exe", "")
            return f"Unlock ({proc})"
        return "Lock current app"

    menu = Menu(
        MenuItem(rpc_label, on_toggle_rpc),
        MenuItem(lock_label, on_toggle_lock),
        Menu.SEPARATOR,
        MenuItem("Reload config", on_reload_config),
        MenuItem("Open config.json", on_open_config),
        Menu.SEPARATOR,
        MenuItem("Quit", on_quit),
    )

    tray = Icon("Discord RPC", make_icon(), "Discord RPC Watcher", menu)
    icon_ref[0] = tray

    def handle_signal(sig, frame):
        logger.info("Termination signal received.")
        engine.stop()
        if icon_ref[0]:
            icon_ref[0].stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Start engine in background and enter tray loop
    engine.start()
    tray.run()


if __name__ == "__main__":
    run_app()
