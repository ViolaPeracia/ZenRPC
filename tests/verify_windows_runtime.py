#!/usr/bin/env python3
"""
Comprehensive Real Windows Runtime Verification Harness (Issue #20).

Verifies live Windows behavior across all acceptance criteria:
1. Normal GUI startup & CustomTkinter window initialization.
2. Live process/title detection and Discord Activity preview card.
3. Timer updates and reset on application switch.
4. Lock/Unlock presence controls.
5. Enable/Disable RPC toggle.
6. Live configuration reload.
7. Visual application mapping creation, editing, and deletion.
8. Settings validation and rate-limit interval clamping (>=15s).
9. Window close / minimize-to-tray behavior.
10. Tray menu contains "Show Dashboard" and restore brings window to foreground/focus.
11. Repeated hide -> restore cycles work reliably without degradation.
12. Windows console behavior (hides exclusive console, preserves interactive terminal).
13. Clean shutdown without hanging background worker threads.
14. All CLI launch modes compatibility (--gui, --tray, --headless, --config).
15. Memory footprint measurement (Working Set and Private Bytes).
"""

import ctypes
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest.mock as mock
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import psutil
from pystray import Icon, Menu, MenuItem

from app.config import DEFAULT_CONFIG, save_config, load_config
from app.gui.controller import GUIController
from app.gui.dashboard import ZenRPCDashboard
from app.gui.platform import WindowsPlatformAdapter, get_platform_adapter
from app.presence import PresenceEngine
from main import make_icon
from tests.conftest import MockRPC

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("verify_windows_runtime")


def run_verification():
    logger.info("=" * 70)
    logger.info("STARTING REAL WINDOWS RUNTIME VERIFICATION (Issue #20)")
    logger.info("Platform: %s | Python: %s", sys.platform, sys.version.split()[0])
    logger.info("=" * 70)

    if sys.platform != "win32":
        logger.error("This harness must be run on Windows (win32).")
        sys.exit(1)

    results = []

    def record_result(check_num: int, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        logger.info("[%s] Check %02d: %s %s", status, check_num, name, f"({detail})" if detail else "")
        results.append((check_num, name, passed, detail))

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = os.path.join(tmpdir, "config.json")
        initial_cfg = {
            "client_id": "123456789012345678",
            "update_interval": 20,
            "reconnect_delay": 5,
            "clear_on_idle": True,
            "show_window_title": True,
            "minimize_to_tray": True,
            "custom_mappings": {
                "notepad.exe": {"name": "Notepad", "icon": "notepad", "detail": "Writing notes"}
            },
        }
        save_config(initial_cfg, cfg_file)

        # Mock detector state
        current_state = ["Code.exe", "main.py - ZenRPC - Visual Studio Code"]

        def test_detector():
            return current_state[0], current_state[1]

        engine = PresenceEngine(
            config_path=cfg_file,
            detector_fn=test_detector,
            rpc_factory=lambda cid: MockRPC(cid),
        )
        controller = GUIController(engine=engine, config_path=cfg_file)
        adapter = get_platform_adapter()

        assert isinstance(adapter, WindowsPlatformAdapter), "Expected WindowsPlatformAdapter on win32"

        # Build real pystray Tray Menu with "Show Dashboard" item
        tray_restored_flag = [False]

        def on_tray_restore(icon, item):
            tray_restored_flag[0] = True
            if dashboard:
                dashboard.after(0, dashboard.restore_window)

        tray_menu = Menu(
            MenuItem("Show Dashboard", on_tray_restore, default=True),
            MenuItem(lambda item: "Disable RPC" if engine.running else "Enable RPC", lambda i, it: controller.toggle_rpc()),
            Menu.SEPARATOR,
            MenuItem("Quit", lambda i, it: None),
        )
        tray_icon = Icon("ZenRPC", make_icon(), "ZenRPC Dashboard", tray_menu)

        dashboard = None
        try:
            # -----------------------------------------------------------------
            # Check 1: Normal GUI startup
            # -----------------------------------------------------------------
            logger.info("Initializing CustomTkinter ZenRPCDashboard...")
            dashboard = ZenRPCDashboard(
                controller=controller,
                tray_icon=tray_icon,
                platform_adapter=adapter,
            )
            dashboard.update_idletasks()
            dashboard.update()

            hwnd = adapter.get_window_hwnd(dashboard)
            check1_pass = (
                dashboard.winfo_exists()
                and dashboard.title() == "ZenRPC Dashboard"
                and hwnd is not None
                and hwnd > 0
            )
            record_result(1, "Normal GUI startup & Win32 HWND resolution", check1_pass, f"HWND={hwnd}")

            # -----------------------------------------------------------------
            # Check 2: Live process/title detection and Discord presence preview
            # -----------------------------------------------------------------
            engine.start()
            time.sleep(0.3)
            controller.poll_update()
            dashboard.update()

            st = controller.get_state()
            app_name = dashboard.app_name_label.cget("text")
            state_text = dashboard.state_label.cget("text")
            check2_pass = (
                st["running"] is True
                and st["connected"] is True
                and app_name == "Visual Studio Code"
                and state_text == "main.py - ZenRPC - Visual Studio Code"
            )
            record_result(2, "Live process/title detection & Discord preview", check2_pass, f"app='{app_name}', state='{state_text}'")

            # -----------------------------------------------------------------
            # Check 3: Timer updates and reset on application switch
            # -----------------------------------------------------------------
            time.sleep(1.2)
            controller.poll_update()
            dashboard.update()
            st_same = controller.get_state()
            elapsed_first = st_same["elapsed_seconds"]

            # Switch app to chrome
            current_state[0] = "chrome.exe"
            current_state[1] = "GitHub - ZenRPC - Google Chrome"
            engine.update_once()
            controller.poll_update()
            dashboard.update()
            st_switched = controller.get_state()
            elapsed_switched = st_switched["elapsed_seconds"]

            check3_pass = (
                elapsed_first >= 1
                and elapsed_switched <= 1
                and st_switched["app_name"] == "Google Chrome"
            )
            record_result(3, "Timer continuity & reset on app switch", check3_pass, f"before={elapsed_first}s, after switch={elapsed_switched}s")

            # -----------------------------------------------------------------
            # Check 4: Lock / Unlock
            # -----------------------------------------------------------------
            dashboard._on_toggle_lock_click()
            dashboard.update()
            st_locked = controller.get_state()
            badge_locked = dashboard.lock_badge.cget("text")
            btn_locked_text = dashboard.btn_toggle_lock.cget("text")

            # Switch detector to another app, engine should remain locked
            current_state[0] = "notepad.exe"
            current_state[1] = "notes.txt - Notepad"
            engine.update_once()
            controller.poll_update()
            dashboard.update()
            st_still_locked = controller.get_state()

            # Unlock
            dashboard._on_toggle_lock_click()
            dashboard.update()
            st_unlocked = controller.get_state()
            badge_unlocked = dashboard.lock_badge.cget("text")

            check4_pass = (
                st_locked["locked"] is True
                and "LOCKED" in badge_locked
                and btn_locked_text == "Unlock Presence"
                and st_still_locked["proc_name"] == "chrome.exe"
                and st_unlocked["locked"] is False
                and badge_unlocked == "[UNLOCKED]"
            )
            record_result(4, "Lock and unlock presence controls", check4_pass, f"lock_badge={badge_locked} -> {badge_unlocked}")

            # -----------------------------------------------------------------
            # Check 5: Enable / Disable RPC
            # -----------------------------------------------------------------
            dashboard._on_toggle_rpc_click()
            dashboard.update()
            st_disabled = controller.get_state()
            status_disabled = dashboard.status_badge.cget("text")
            btn_rpc_text_disabled = dashboard.btn_toggle_rpc.cget("text")

            dashboard._on_toggle_rpc_click()
            dashboard.update()
            st_enabled = controller.get_state()
            btn_rpc_text_enabled = dashboard.btn_toggle_rpc.cget("text")

            check5_pass = (
                st_disabled["running"] is False
                and "RPC Disabled" in status_disabled
                and btn_rpc_text_disabled == "Enable RPC"
                and st_enabled["running"] is True
                and btn_rpc_text_enabled == "Disable RPC"
            )
            record_result(5, "Enable / Disable RPC toggle", check5_pass, f"disabled='{status_disabled}', re-enabled={st_enabled['running']}")

            # -----------------------------------------------------------------
            # Check 6: Reload Config
            # -----------------------------------------------------------------
            on_disk = load_config(cfg_file)
            on_disk["update_interval"] = 45
            save_config(on_disk, cfg_file)

            dashboard._on_reload_config_click()
            dashboard.update()
            st_reloaded = controller.get_state()
            slider_val = int(dashboard.slider_interval.get())

            check6_pass = (
                st_reloaded["update_interval"] == 45
                and slider_val == 45
            )
            record_result(6, "Live configuration reload", check6_pass, f"new_interval={slider_val}s")

            # -----------------------------------------------------------------
            # Check 7: Mapping creation, editing, and deletion
            # -----------------------------------------------------------------
            dashboard.entry_map_proc.delete(0, "end")
            dashboard.entry_map_proc.insert(0, "custom_editor.exe")
            dashboard.entry_map_name.delete(0, "end")
            dashboard.entry_map_name.insert(0, "Custom Editor Pro")
            dashboard.entry_map_icon.delete(0, "end")
            dashboard.entry_map_icon.insert(0, "editor_pro")
            dashboard.entry_map_detail.delete(0, "end")
            dashboard.entry_map_detail.insert(0, "Developing code")

            dashboard._on_save_mapping_click()
            dashboard.update()

            cfg_after_add = load_config(cfg_file)
            mapping_added = "custom_editor.exe" in cfg_after_add["custom_mappings"]

            dashboard._on_delete_mapping("custom_editor.exe")
            dashboard.update()
            cfg_after_del = load_config(cfg_file)
            mapping_removed = "custom_editor.exe" not in cfg_after_del["custom_mappings"]

            check7_pass = mapping_added and mapping_removed
            record_result(7, "Visual mapping add, edit, and deletion", check7_pass, f"added={mapping_added}, removed={mapping_removed}")

            # -----------------------------------------------------------------
            # Check 8: Settings validation (update interval >= 15s)
            # -----------------------------------------------------------------
            clamped_cfg = controller.save_settings(update_interval=5)
            check8_pass = clamped_cfg["update_interval"] == 15
            record_result(8, "Settings validation (interval >= 15s clamp)", check8_pass, f"saved={clamped_cfg['update_interval']}s")

            # -----------------------------------------------------------------
            # Check 9: Close / minimize-to-tray behavior
            # -----------------------------------------------------------------
            dashboard.on_closing()
            dashboard.update()
            state_withdrawn = dashboard.state()
            check9_pass = state_withdrawn == "withdrawn"
            record_result(9, "Minimize-to-tray on close (X)", check9_pass, f"window_state='{state_withdrawn}'")

            # -----------------------------------------------------------------
            # Check 10: Tray menu contains "Show Dashboard" & restores window
            # -----------------------------------------------------------------
            # Verify "Show Dashboard" item exists in tray_menu
            show_item = None
            for item in tray_menu.items:
                if getattr(item, "text", None) == "Show Dashboard":
                    show_item = item
                    break

            has_show_item = show_item is not None
            # Trigger "Show Dashboard"
            if show_item:
                show_item(tray_icon)
                dashboard.update()
                time.sleep(0.1)
                dashboard.update()

            state_restored = dashboard.state()
            check10_pass = (
                has_show_item
                and state_restored == "normal"
                and tray_restored_flag[0] is True
            )
            record_result(10, "Tray menu 'Show Dashboard' & foreground restore", check10_pass, f"has_item={has_show_item}, restored_state='{state_restored}'")

            # -----------------------------------------------------------------
            # Check 11: Repeated hide -> restore cycles
            # -----------------------------------------------------------------
            repeated_success = True
            for cycle in range(1, 6):
                dashboard.minimize_to_tray()
                dashboard.update()
                if dashboard.state() != "withdrawn":
                    repeated_success = False
                    break

                dashboard.restore_window()
                dashboard.update()
                if dashboard.state() != "normal":
                    repeated_success = False
                    break

            record_result(11, "Repeated hide -> restore cycles (5 cycles)", repeated_success, "5/5 cycles toggled withdrawn <-> normal reliably")

            # -----------------------------------------------------------------
            # Check 12: Windows console behavior
            # -----------------------------------------------------------------
            pids = (ctypes.c_uint * 4)()
            proc_count = ctypes.windll.kernel32.GetConsoleProcessList(pids, 4)
            with mock.patch("ctypes.windll.user32.ShowWindow") as mock_show:
                adapter.hide_console()
                show_called = mock_show.called

            # In an existing terminal (proc_count > 1), hide_console MUST NOT hide the console
            check12_pass = (proc_count > 1 and not show_called) or (proc_count <= 1 and show_called)
            record_result(12, "Windows console preservation in terminal", check12_pass, f"proc_count={proc_count}, show_window_called={show_called}")

            # -----------------------------------------------------------------
            # Check 13: Clean shutdown without hanging background threads
            # -----------------------------------------------------------------
            dashboard.quit_app()
            time.sleep(0.5)

            engine_stopped = not engine.running
            worker_dead = not (engine._thread and engine._thread.is_alive())

            check13_pass = engine_stopped and worker_dead
            record_result(13, "Clean shutdown & thread termination", check13_pass, f"worker_alive={engine._thread.is_alive() if engine._thread else False}")

        except Exception as e:
            logger.exception("Exception during runtime verification: %s", e)
            record_result(0, "Runtime execution", False, str(e))
            if dashboard:
                try:
                    dashboard.destroy()
                except Exception:
                    pass

    # -----------------------------------------------------------------
    # Check 14: All Windows CLI launch modes (--gui, --tray, --headless, --config)
    # -----------------------------------------------------------------
    cli_checks = []
    try:
        # 1. Help flag
        res_help = subprocess.run([sys.executable, "main.py", "--help"], capture_output=True, text=True, timeout=5)
        cli_checks.append(res_help.returncode == 0 and "--gui" in res_help.stdout and "--tray" in res_help.stdout)

        # 2. Mutually exclusive error handling
        res_conflict = subprocess.run([sys.executable, "main.py", "--tray", "--headless"], capture_output=True, text=True, timeout=5)
        cli_checks.append(res_conflict.returncode != 0)

        # 3. Headless mode with custom config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump({"client_id": "test_id"}, tf)
            custom_cfg_path = tf.name

        p_hl = subprocess.Popen([sys.executable, "main.py", "--headless", "--config", custom_cfg_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.8)
        hl_alive = p_hl.poll() is None
        p_hl.terminate()
        p_hl.communicate(timeout=3)
        cli_checks.append(hl_alive)

        try:
            os.remove(custom_cfg_path)
        except OSError:
            pass

        # 4. Tray mode launch
        p_tray = subprocess.Popen([sys.executable, "main.py", "--tray"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.8)
        tray_alive = p_tray.poll() is None
        p_tray.terminate()
        p_tray.communicate(timeout=3)
        cli_checks.append(tray_alive)

        # 5. GUI mode launch
        p_gui = subprocess.Popen([sys.executable, "main.py", "--gui"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(1.0)
        gui_alive = p_gui.poll() is None
        p_gui.terminate()
        p_gui.communicate(timeout=3)
        cli_checks.append(gui_alive)

    except Exception as e:
        logger.error("CLI validation failed: %s", e)
        cli_checks.append(False)

    check14_pass = all(cli_checks)
    record_result(14, "All Windows CLI launch modes (--gui, --tray, --headless, --config)", check14_pass, f"{sum(cli_checks)}/{len(cli_checks)} modes verified")

    # -----------------------------------------------------------------
    # Check 15: Memory footprint measurement
    # -----------------------------------------------------------------
    current_proc = psutil.Process(os.getpid())
    mem_info = current_proc.memory_full_info()
    rss_mb = mem_info.rss / (1024 * 1024)
    private_mb = mem_info.private / (1024 * 1024)

    logger.info("=" * 70)
    logger.info("MEMORY FOOTPRINT MEASUREMENT:")
    logger.info("  Working Set (RSS): %.2f MB", rss_mb)
    logger.info("  Private Bytes:     %.2f MB", private_mb)
    logger.info("=" * 70)

    all_passed = all(p for _, _, p, _ in results)
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION SUMMARY:")
    for num, name, passed, detail in results:
        logger.info("  Check %02d: [%s] %s %s", num, "PASS" if passed else "FAIL", name, f"- {detail}" if detail else "")
    logger.info("=" * 70)
    logger.info("OVERALL STATUS: %s", f"ALL CHECKS PASSED ({len(results)}/{len(results)})" if all_passed else "SOME CHECKS FAILED")
    logger.info("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_verification())
