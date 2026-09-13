#!/usr/bin/env python3
"""
Real Linux X11/XWayland Runtime Verification Harness (Issue #9).

Verifies live behavior on Linux XWayland (DISPLAY=:1):
1. xdotool 2-second timeout enforcement in _run_cmd.
2. Real foreground window detection via get_active_window_info().
3. Multibyte Unicode window title handling (Vietnamese, CJK, Emoji).
4. Title-only window title changes preserve elapsed timer in PresenceEngine.
5. Application switching resets elapsed timer in PresenceEngine.
6. Window unmap/destroy / idle clears presence when clear_on_idle=True.
7. Recognized application mappings (details, icon, application name).
8. Unrecognized application fallback, process exit detection, and replacement.
9. Clean start/stop lifecycle of PresenceEngine background worker thread.
10. Clean shutdown handling on SIGINT and SIGTERM.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import List, Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from Xlib import X, display, protocol
from app.detector import _run_cmd, get_active_window_info
from app.presence import PresenceEngine
from tests.conftest import MockRPC

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("verify_linux_runtime")


class X11WindowManager:
    """Helper to create, title, focus, unmap, and destroy real X11 windows."""

    def __init__(self, display_name: Optional[str] = None):
        self.display_name = display_name or os.environ.get("DISPLAY", ":1")
        self.d = display.Display(self.display_name)
        self.screen = self.d.screen()
        self.root = self.screen.root
        self.created_windows = []

    def create_window(
        self,
        title: str,
        pid: int,
        x: int = 100,
        y: int = 100,
        width: int = 400,
        height: int = 300,
    ):
        window = self.root.create_window(
            x,
            y,
            width,
            height,
            1,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=self.screen.white_pixel,
            event_mask=X.ExposureMask | X.StructureNotifyMask,
        )
        self.created_windows.append(window)
        self.set_title(window, title)
        self.set_pid(window, pid)
        window.map()
        self.d.sync()
        time.sleep(0.15)
        return window

    def set_title(self, window, title: str):
        try:
            window.set_wm_name(title)
        except Exception:
            pass  # Fallback for non-latin1 titles in legacy WM_NAME
        net_wm_name = self.d.intern_atom("_NET_WM_NAME")
        utf8_string = self.d.intern_atom("UTF8_STRING")
        window.change_property(net_wm_name, utf8_string, 8, title.encode("utf-8"))
        self.d.sync()
        time.sleep(0.1)

    def set_pid(self, window, pid: int):
        net_wm_pid = self.d.intern_atom("_NET_WM_PID")
        cardinal = self.d.intern_atom("CARDINAL")
        window.change_property(net_wm_pid, cardinal, 32, [pid])
        self.d.sync()
        time.sleep(0.1)

    def activate(self, window):
        try:
            subprocess.run(
                ["xdotool", "windowactivate", str(window.id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except Exception:
            pass
        self.d.sync()
        time.sleep(0.2)

    def unmap(self, window):
        try:
            window.unmap()
            self.d.sync()
            time.sleep(0.15)
        except Exception as e:
            logger.debug("Error unmapping window: %s", e)

    def destroy(self, window):
        try:
            if window in self.created_windows:
                self.created_windows.remove(window)
            window.destroy()
            self.d.sync()
            time.sleep(0.15)
        except Exception as e:
            logger.debug("Error destroying window: %s", e)

    def cleanup_all(self):
        for window in list(self.created_windows):
            try:
                window.destroy()
            except Exception:
                pass
        self.created_windows.clear()
        try:
            self.d.sync()
            self.d.close()
        except Exception:
            pass


class ProcessManager:
    """Manages simulated child processes for real PID inspection."""

    def __init__(self):
        self.processes: List[subprocess.Popen] = []

    def spawn(self, name: str) -> subprocess.Popen:
        p = subprocess.Popen(["bash", "-c", f"exec -a {name} sleep 120"])
        self.processes.append(p)
        time.sleep(0.1)
        return p

    def kill(self, p: subprocess.Popen):
        try:
            if p in self.processes:
                self.processes.remove(p)
            p.kill()
            p.wait(timeout=2)
        except Exception:
            pass

    def cleanup_all(self):
        for p in list(self.processes):
            try:
                p.kill()
                p.wait(timeout=1)
            except Exception:
                pass
        self.processes.clear()


def make_test_config(temp_dir: str) -> str:
    """Creates a temporary config.json with known mappings."""
    cfg = {
        "client_id": "999888777666555444",
        "update_interval": 15,
        "reconnect_delay": 30,
        "show_window_title": True,
        "clear_on_idle": True,
        "custom_mappings": {
            "code": {
                "name": "Visual Studio Code",
                "icon": "vscode",
                "detail": "Coding",
            },
            "firefox": {
                "name": "Firefox",
                "icon": "firefox",
                "detail": "Browsing",
            },
        },
    }
    cfg_file = os.path.join(temp_dir, "test_config.json")
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return cfg_file


def verify_timeout_enforcement():
    """Verify xdotool / _run_cmd 2-second timeout enforcement."""
    logger.info("=== Check 1: 2-Second Timeout Enforcement ===")
    t0 = time.time()
    res = _run_cmd(["sleep", "5"], timeout=2)
    elapsed = time.time() - t0

    assert res == "", f"Expected empty string on timeout, got {res!r}"
    assert 1.9 <= elapsed < 2.5, f"Expected elapsed time ~2s, got {elapsed:.2f}s"
    logger.info(
        "✓ PASS: _run_cmd timeout enforced in %.2fs returning empty string.", elapsed
    )


def verify_foreground_detection(wm: X11WindowManager):
    """Verify real foreground window detection on XWayland."""
    logger.info("=== Check 2: Real Foreground Window Detection ===")
    win = wm.create_window(title="VS Code Window", pid=os.getpid())
    wm.activate(win)

    proc_name, title = get_active_window_info()
    assert (
        proc_name == "python"
    ), f"Expected proc_name 'python', got {proc_name!r}"
    assert (
        title == "VS Code Window"
    ), f"Expected title 'VS Code Window', got {title!r}"
    logger.info(
        "✓ PASS: Foreground window detected correctly: ('%s', '%s')",
        proc_name,
        title,
    )
    return win


def verify_unicode_titles(wm: X11WindowManager, win):
    """Verify multibyte Unicode window title handling."""
    logger.info("=== Check 3: Multibyte Unicode Window Titles ===")
    unicode_title = "Dự án ZenRPC 🚀"
    wm.set_title(win, unicode_title)
    wm.activate(win)

    proc_name, title = get_active_window_info()
    assert (
        proc_name == "python"
    ), f"Expected proc_name 'python', got {proc_name!r}"
    assert (
        title == unicode_title
    ), f"Expected title {unicode_title!r}, got {title!r}"
    logger.info("✓ PASS: Multibyte Unicode title verified: '%s'", title)


def verify_presence_engine_timer_and_switch(
    wm: X11WindowManager, win_a, pm: ProcessManager, cfg_path: str
):
    """
    Verify:
    - PresenceEngine connects and establishes initial presence.
    - Title-only change preserves elapsed timer.
    - Application switching resets elapsed timer.
    - Window unmap/destroy clears presence on idle.
    """
    logger.info(
        "=== Check 4: PresenceEngine Timer Preservation on Title-Only Change ==="
    )
    mock_rpc = MockRPC("999888777666555444")
    engine = PresenceEngine(config_path=cfg_path, rpc_factory=lambda cid: mock_rpc)
    connected = engine.connect()
    assert connected is True, "Expected engine.connect() to succeed"
    assert mock_rpc.connected is True, "Expected mock_rpc.connected to be True"

    # Window A is active with Unicode title from Check 3
    wm.activate(win_a)
    engine.update_once()

    assert len(mock_rpc.updates) == 1, (
        f"Expected 1 update, got {len(mock_rpc.updates)}"
    )
    first_update = mock_rpc.updates[0]
    initial_start_ts = first_update["start"]
    assert initial_start_ts == engine.current_proc_start_time
    assert first_update["state"] == "Dự án ZenRPC 🚀"
    logger.info(
        "✓ Initial presence set: app=%s, start=%d, state='%s'",
        engine.current_proc,
        initial_start_ts,
        first_update["state"],
    )

    # Sleep so system clock advances
    time.sleep(1.2)

    # Title-only change on Window A
    wm.set_title(win_a, "VS Code Window - modified")
    wm.activate(win_a)
    engine.update_once()

    assert len(mock_rpc.updates) == 2, (
        f"Expected 2 updates, got {len(mock_rpc.updates)}"
    )
    second_update = mock_rpc.updates[1]
    assert second_update["start"] == initial_start_ts, (
        f"Expected timer preserved ({initial_start_ts}), got {second_update['start']}"
    )
    assert second_update["state"] == "VS Code Window - modified"
    logger.info(
        "✓ PASS: Title-only change preserved start timer: %d == %d",
        second_update["start"],
        initial_start_ts,
    )

    logger.info(
        "=== Check 5: Application Switching Resets Elapsed Timer ==="
    )
    time.sleep(1.2)
    p_browser = pm.spawn("firefox")
    win_b = wm.create_window(
        title="Browser Window",
        pid=p_browser.pid,
        x=200,
        y=200,
    )
    wm.activate(win_b)

    proc_name, title = get_active_window_info()
    assert proc_name == "firefox", f"Expected 'firefox', got {proc_name!r}"
    assert title == "Browser Window", f"Expected 'Browser Window', got {title!r}"

    engine.update_once()
    assert len(mock_rpc.updates) == 3, (
        f"Expected 3 updates, got {len(mock_rpc.updates)}"
    )
    third_update = mock_rpc.updates[2]
    assert third_update["start"] > initial_start_ts, (
        f"Expected timer reset (> {initial_start_ts}), got {third_update['start']}"
    )
    assert third_update["details"] == "Browsing"
    assert third_update["large_image"] == "firefox"
    logger.info(
        "✓ PASS: App switch to 'firefox' reset start timer: %d > %d",
        third_update["start"],
        initial_start_ts,
    )

    logger.info(
        "=== Check 6: Window Unmap/Destroy Triggers Idle Clearing ==="
    )
    # Unmap both windows so no window remains active
    wm.unmap(win_b)
    wm.unmap(win_a)
    proc_unmapped, title_unmapped = get_active_window_info()
    assert proc_unmapped is None and title_unmapped is None, (
        f"Expected (None, None) when unmapped, got ({proc_unmapped}, {title_unmapped})"
    )

    engine.update_once()
    assert mock_rpc.cleared is True, "Expected presence cleared on idle unmap"
    assert engine.presence_cleared is True
    logger.info("✓ PASS: Window unmap triggers idle clearing")

    # Destroy both windows and kill process
    wm.destroy(win_b)
    wm.destroy(win_a)
    pm.kill(p_browser)

    proc_destroyed, title_destroyed = get_active_window_info()
    assert proc_destroyed is None and title_destroyed is None
    logger.info("✓ PASS: Window destroy keeps idle state (None, None)")

    return engine, mock_rpc


def verify_recognized_app(
    wm: X11WindowManager, pm: ProcessManager, engine: PresenceEngine, mock_rpc: MockRPC
):
    """Verify recognized application mapping."""
    logger.info(
        "=== Check 7: Recognized Application Mapping ==="
    )
    time.sleep(1.2)
    p_code = pm.spawn("code")
    win_code = wm.create_window(
        title="main.py - ZenRPC", pid=p_code.pid, x=150, y=150
    )
    wm.activate(win_code)

    proc_name, title = get_active_window_info()
    assert proc_name == "code", f"Expected 'code', got {proc_name!r}"
    assert title == "main.py - ZenRPC"

    engine.update_once()
    last_update = mock_rpc.updates[-1]
    assert last_update["details"] == "Coding"
    assert last_update["large_image"] == "vscode"
    assert last_update["large_text"] == "Visual Studio Code"
    assert last_update["state"] == "main.py - ZenRPC"
    logger.info(
        "✓ PASS: Recognized app 'code' mapped -> detail='%s', icon='%s', app_name='%s'",
        last_update["details"],
        last_update["large_image"],
        last_update["large_text"],
    )

    wm.destroy(win_code)
    pm.kill(p_code)


def verify_unrecognized_and_process_exit(
    wm: X11WindowManager, pm: ProcessManager, engine: PresenceEngine, mock_rpc: MockRPC
):
    """Verify unrecognized app fallback, process exit clearing, and replacement."""
    logger.info(
        "=== Check 8: Unrecognized App Fallback & Process Exit/Replacement ==="
    )
    time.sleep(1.2)
    p_unknown = pm.spawn("zenrpc_custom_tool")
    win_unknown = wm.create_window(
        title="Custom Tool Window", pid=p_unknown.pid, x=180, y=180
    )
    wm.activate(win_unknown)

    proc_name, _ = get_active_window_info()
    assert (
        proc_name == "zenrpc_custom_tool"
    ), f"Expected 'zenrpc_custom_tool', got {proc_name!r}"

    engine.update_once()
    last_update = mock_rpc.updates[-1]
    assert last_update["details"] == "Using zenrpc_custom_tool"
    assert "large_image" not in last_update
    assert last_update["state"] == "Custom Tool Window"
    logger.info(
        "✓ PASS: Unrecognized app fallback -> detail='%s', no icon, state='%s'",
        last_update["details"],
        last_update["state"],
    )

    # Terminate process while window is still active
    pm.kill(p_unknown)
    time.sleep(0.2)

    proc_after, title_after = get_active_window_info()
    assert proc_after is None and title_after is None, (
        f"Expected (None, None) after process death, got ({proc_after}, {title_after})"
    )
    logger.info("✓ PASS: Dead PID /proc inspection returned (None, None)")

    engine.update_once()
    assert mock_rpc.cleared is True, "Expected mock_rpc to clear on process exit"
    assert engine.presence_cleared is True
    logger.info("✓ PASS: Presence cleared upon active process termination")

    # Replace with a new valid process and window
    p_rep = pm.spawn("firefox")
    wm.set_pid(win_unknown, p_rep.pid)
    wm.set_title(win_unknown, "Restored Browser")
    wm.activate(win_unknown)

    proc_restored, title_restored = get_active_window_info()
    assert proc_restored == "firefox"
    assert title_restored == "Restored Browser"

    engine.update_once()
    assert mock_rpc.cleared is False, "Expected presence restored after process replacement"
    assert mock_rpc.updates[-1]["details"] == "Browsing"
    logger.info("✓ PASS: Process replacement restored presence: '%s'", proc_restored)

    wm.destroy(win_unknown)
    pm.kill(p_rep)


def verify_lifecycle_and_signals(cfg_path: str):
    """Verify PresenceEngine background thread lifecycle and clean shutdown on signals."""
    logger.info(
        "=== Check 9: PresenceEngine Thread Start/Stop Lifecycle ==="
    )
    mock = MockRPC("999888777666555444")
    engine = PresenceEngine(config_path=cfg_path, rpc_factory=lambda cid: mock)

    engine.start()
    assert engine.running is True, "Expected engine.running is True"
    assert engine.connected is True, "Expected engine.connected is True"
    assert engine._thread is not None and engine._thread.is_alive() is True
    logger.info("✓ PASS: Engine thread started and connected")

    engine.stop()
    assert engine.running is False, "Expected engine.running is False"
    assert engine.connected is False, "Expected engine.connected is False"
    assert engine._thread.is_alive() is False, "Expected engine thread terminated"
    logger.info("✓ PASS: Engine stopped, thread joined, RPC disconnected")

    logger.info(
        "=== Check 10: Clean Shutdown on SIGINT and SIGTERM ==="
    )
    shutdown_script = f"""
import signal, sys, time
from app.presence import PresenceEngine
from tests.conftest import MockRPC

mock = MockRPC('999888777666555444')
engine = PresenceEngine(config_path={cfg_path!r}, rpc_factory=lambda cid: mock)

def on_signal(sig, frame):
    engine.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, on_signal)
signal.signal(signal.SIGTERM, on_signal)
engine.start()

while True:
    time.sleep(0.1)
"""

    # Test SIGINT
    p_sigint = subprocess.Popen([sys.executable, "-c", shutdown_script])
    time.sleep(0.6)
    p_sigint.send_signal(signal.SIGINT)
    ret_sigint = p_sigint.wait(timeout=5)
    assert (
        ret_sigint == 0
    ), f"Expected exit code 0 on SIGINT, got {ret_sigint}"
    logger.info("✓ PASS: Clean exit on SIGINT (exit code: 0)")

    # Test SIGTERM
    p_sigterm = subprocess.Popen([sys.executable, "-c", shutdown_script])
    time.sleep(0.6)
    p_sigterm.send_signal(signal.SIGTERM)
    ret_sigterm = p_sigterm.wait(timeout=5)
    assert (
        ret_sigterm == 0
    ), f"Expected exit code 0 on SIGTERM, got {ret_sigterm}"
    logger.info("✓ PASS: Clean exit on SIGTERM (exit code: 0)")


def main():
    logger.info(
        "Starting Linux X11/XWayland Runtime Verification on DISPLAY=%s",
        os.environ.get("DISPLAY", ":1"),
    )

    # In X11/XWayland test harness, bypass native Wayland compositor IPC so external
    # developer desktop windows do not interfere with synthetic X11 window lifecycle.
    import app.detector
    app.detector._get_active_niri = lambda timeout=1: (None, None)

    temp_dir = tempfile.mkdtemp(prefix="zenrpc_verify_")
    cfg_path = make_test_config(temp_dir)

    wm = X11WindowManager()
    pm = ProcessManager()

    try:
        # 1. Timeout enforcement
        verify_timeout_enforcement()

        # 2. Real foreground window detection
        win_a = verify_foreground_detection(wm)

        # 3. Multibyte Unicode window titles
        verify_unicode_titles(wm, win_a)

        # 4, 5, 6. Timer preservation, app switching reset, and idle unmap/destroy
        engine, mock_rpc = verify_presence_engine_timer_and_switch(
            wm, win_a, pm, cfg_path
        )

        # 7. Recognized application mapping
        verify_recognized_app(wm, pm, engine, mock_rpc)

        # 8. Unrecognized application fallback & process exit/replacement
        verify_unrecognized_and_process_exit(wm, pm, engine, mock_rpc)

        # 9 & 10. Engine lifecycle and clean signal shutdown
        verify_lifecycle_and_signals(cfg_path)

        logger.info(
            "============================================================"
        )
        logger.info("ALL 10 RUNTIME VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        logger.info(
            "============================================================"
        )
        return 0

    except Exception as e:
        logger.exception("Runtime verification failed: %s", e)
        return 1

    finally:
        logger.info("Cleaning up test windows, processes, and temp files...")
        wm.cleanup_all()
        pm.cleanup_all()
        try:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
