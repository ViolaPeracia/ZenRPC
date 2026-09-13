import argparse
import ctypes
import logging
import os
import signal
import subprocess
import sys
import threading
import time

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from app.config import get_config_path
from app.presence import PresenceEngine

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zenrpc")

# Global active references for robust signal handling and clean shutdown
_active_engine = [None]
_active_tray = [None]
_active_dashboard = [None]


def global_signal_handler(sig, frame):
    """Unified signal handler guaranteeing immediate, clean exit on SIGINT/SIGTERM."""
    logger.info("Termination signal received. Shutting down ZenRPC...")
    if _active_dashboard[0]:
        try:
            _active_dashboard[0].quit_app()
        except Exception:
            pass
    if _active_engine[0]:
        try:
            _active_engine[0].stop()
        except Exception:
            pass
    if _active_tray[0]:
        try:
            _active_tray[0].stop()
        except Exception:
            pass
    sys.exit(0)


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


def hide_windows_console():
    """Hides console window on Windows when not in persistent terminal."""
    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass


def parse_args(args=None):
    """Parses command line arguments for ZenRPC."""
    parser = argparse.ArgumentParser(
        description="ZenRPC - Discord Rich Presence Client",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--gui",
        action="store_true",
        help="Launch desktop GUI dashboard (default)",
    )
    mode_group.add_argument(
        "--tray",
        action="store_true",
        help="Launch in system tray only mode",
    )
    mode_group.add_argument(
        "--headless",
        action="store_true",
        help="Launch in headless console mode without GUI or tray",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom config.json file",
    )
    return parser.parse_args(args)


def run_headless(config_path=None):
    """Runs ZenRPC in headless mode without GUI or tray icon."""
    logger.info("Starting ZenRPC in headless mode...")
    engine = PresenceEngine(config_path=config_path)
    _active_engine[0] = engine

    engine.start()
    logger.info("ZenRPC running in headless mode. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        global_signal_handler(None, None)


def run_tray(config_path=None):
    """Runs ZenRPC in tray-only mode (legacy main thread tray event loop)."""
    hide_windows_console()
    engine = PresenceEngine(config_path=config_path)
    _active_engine[0] = engine

    def refresh_icon():
        if _active_tray[0]:
            _active_tray[0].icon = make_icon(locked=engine.locked)
            _active_tray[0].title = "ZenRPC [LOCKED]" if engine.locked else "ZenRPC"

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
        open_file_externally(get_config_path(config_path))

    def on_quit(icon, item):
        logger.info("Shutting down ZenRPC...")
        global_signal_handler(None, None)

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

    tray = Icon("ZenRPC", make_icon(), "ZenRPC", menu)
    _active_tray[0] = tray

    # Start engine in background and enter tray loop
    engine.start()
    tray.run()


def run_gui(config_path=None):
    """Runs ZenRPC with CustomTkinter GUI dashboard and optional background tray integration."""
    hide_windows_console()

    from app.gui.controller import GUIController
    from app.gui.dashboard import ZenRPCDashboard

    engine = PresenceEngine(config_path=config_path)
    _active_engine[0] = engine
    controller = GUIController(engine=engine, config_path=config_path)

    # Initialize optional system tray icon in background daemon thread
    try:
        def on_tray_restore(icon, item):
            if _active_dashboard[0]:
                _active_dashboard[0].after(0, _active_dashboard[0].restore_window)

        def on_tray_toggle_rpc(icon, item):
            controller.toggle_rpc()
            controller.poll_update()

        def on_tray_toggle_lock(icon, item):
            controller.toggle_lock()
            controller.poll_update()

        def on_tray_reload(icon, item):
            controller.reload_config()
            controller.poll_update()
            if _active_dashboard[0]:
                _active_dashboard[0].after(0, _active_dashboard[0]._load_settings_values)
                _active_dashboard[0].after(0, _active_dashboard[0]._refresh_mappings_list)

        def on_tray_quit(icon, item):
            global_signal_handler(None, None)

        tray_menu = Menu(
            MenuItem("Show Dashboard", on_tray_restore, default=True),
            MenuItem(lambda item: "Disable RPC" if engine.running else "Enable RPC", on_tray_toggle_rpc),
            MenuItem(
                lambda item: f"Unlock ({(engine.locked_proc or '?').replace('.exe', '')})"
                if engine.locked
                else "Lock current app",
                on_tray_toggle_lock,
            ),
            Menu.SEPARATOR,
            MenuItem("Reload config", on_tray_reload),
            MenuItem("Open config.json", lambda item: open_file_externally(controller.config_path)),
            Menu.SEPARATOR,
            MenuItem("Quit", on_tray_quit),
        )

        tray = Icon("ZenRPC", make_icon(), "ZenRPC Dashboard", tray_menu)
        tray_thread = threading.Thread(target=tray.run, daemon=True)
        tray_thread.start()
        _active_tray[0] = tray
        logger.info("System tray icon initialized.")
    except Exception as e:
        logger.info("System tray not available or failed to initialize: %s", e)
        _active_tray[0] = None

    # Start presence engine in background
    engine.start()

    # Create dashboard
    app = ZenRPCDashboard(controller=controller, tray_icon=_active_tray[0])
    _active_dashboard[0] = app

    def _poll_signals():
        if _active_dashboard[0]:
            try:
                _active_dashboard[0].after(200, _poll_signals)
            except Exception:
                pass

    app.after(200, _poll_signals)
    app.mainloop()


def run_app():
    """Main application entry point dispatching to selected mode."""
    signal.signal(signal.SIGINT, global_signal_handler)
    signal.signal(signal.SIGTERM, global_signal_handler)

    args = parse_args()

    if args.headless:
        run_headless(config_path=args.config)
    elif args.tray:
        run_tray(config_path=args.config)
    else:
        # Default: attempt GUI mode; fall back gracefully to tray or headless if display unavailable
        try:
            run_gui(config_path=args.config)
        except Exception as e:
            logger.warning("GUI unavailable (%s). Falling back to system tray / headless mode.", e)
            try:
                run_tray(config_path=args.config)
            except Exception as e_tray:
                logger.warning("System tray unavailable (%s). Falling back to headless mode.", e_tray)
                run_headless(config_path=args.config)


if __name__ == "__main__":
    if sys.platform.startswith("linux") and not os.environ.get("_ZENRPC_REEXECED"):
        user_lib = os.path.expanduser("~/.local/lib")
        tk_so = os.path.join(user_lib, "libtk8.6.so")
        cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isfile(tk_so) and user_lib not in cur_ld.split(":"):
            new_env = os.environ.copy()
            new_env["_ZENRPC_REEXECED"] = "1"
            new_env["LD_LIBRARY_PATH"] = f"{user_lib}:{cur_ld}" if cur_ld else user_lib
            new_env["TK_LIBRARY"] = os.path.expanduser("~/.local/lib/tk8.6")
            os.execve(sys.executable, [sys.executable] + sys.argv, new_env)

    run_app()
