import logging
import os
import subprocess
import sys

logger = logging.getLogger("zenrpc")

_LINUX_TOOLS_WARNED = False


try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None


def _get_active_windows():
    """
    Detects active window on Windows using win32gui and psutil.
    Safely handles missing windows, invalid HWND/PIDs, terminated/zombie processes,
    empty/whitespace titles, and platform exceptions by returning (None, None).
    """
    _wgui = win32gui
    _wproc = win32process
    _psutil = psutil

    if _wgui is None or _wproc is None or _psutil is None:
        try:
            import psutil as _psutil
            import win32gui as _wgui
            import win32process as _wproc
        except ImportError as e:
            logger.debug("Windows detection modules not available: %s", e)
            return None, None

    try:
        hwnd = _wgui.GetForegroundWindow()
        if not hwnd:
            return None, None

        title = ""
        try:
            raw_title = _wgui.GetWindowText(hwnd)
            if isinstance(raw_title, str):
                title = raw_title.strip()
        except Exception as e:
            logger.debug("Failed to retrieve window text for HWND %s: %s", hwnd, e)
            title = ""

        try:
            _, pid = _wproc.GetWindowThreadProcessId(hwnd)
        except Exception as e:
            logger.debug("Failed to get process ID for HWND %s: %s", hwnd, e)
            return None, None

        if pid is None or not isinstance(pid, int) or pid <= 0:
            return None, None

        try:
            proc = _psutil.Process(pid)
            if hasattr(proc, "is_running") and not proc.is_running():
                return None, None
            raw_name = proc.name()
        except (getattr(_psutil, "NoSuchProcess", Exception),
                getattr(_psutil, "AccessDenied", Exception),
                getattr(_psutil, "ZombieProcess", Exception)) as e:
            logger.debug("psutil process error for PID %s: %s", pid, e)
            return None, None
        except Exception as e:
            logger.debug("Unexpected error inspecting PID %s: %s", pid, e)
            return None, None

        if not raw_name or not isinstance(raw_name, str) or not raw_name.strip():
            return None, None

        proc_name = raw_name.strip()
        return proc_name, title

    except Exception as e:
        logger.debug("Windows window detection error: %s", e)
        return None, None


def _run_cmd(cmd, timeout=2):
    """Executes a command with strict timeout and captures stdout."""
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=timeout)
        return res.decode(errors="ignore").strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return ""
    except FileNotFoundError:
        global _LINUX_TOOLS_WARNED
        if not _LINUX_TOOLS_WARNED:
            logger.warning("Required tool '%s' not found on system PATH.", cmd[0])
            _LINUX_TOOLS_WARNED = True
        return ""
    except Exception as e:
        logger.debug("Command %s failed: %s", cmd, e)
        return ""


def _get_linux_process_name(pid):
    """Directly reads /proc/<pid>/cmdline or /proc/<pid>/comm without spawning cat."""
    # First attempt: cmdline gives full, non-truncated binary name
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
        if raw:
            first_arg = raw.split(b"\x00")[0].decode(errors="ignore")
            name = os.path.basename(first_arg).strip()
            if name:
                return name.lower()
    except Exception:
        pass

    # Fallback attempt: comm
    try:
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8", errors="ignore") as f:
            comm = f.read().strip()
            if comm:
                return comm.lower()
    except Exception:
        pass

    return "unknown"


def _get_active_linux():
    """
    Detects active window on Linux via X11 (xdotool).
    On pure Wayland sessions where xdotool cannot query active windows,
    gracefully returns (None, None).
    """
    win_id = _run_cmd(["xdotool", "getactivewindow"], timeout=2)
    if not win_id:
        return None, None

    title = _run_cmd(["xdotool", "getwindowname", win_id], timeout=2)
    pid_str = _run_cmd(["xdotool", "getwindowpid", win_id], timeout=2)

    if pid_str and pid_str.isdigit():
        proc_name = _get_linux_process_name(int(pid_str))
        return proc_name, title

    # Window has no PID (e.g. desktop window or client without _NET_WM_PID)
    return "unknown", title


def get_active_window_info():
    """
    Returns (process_name, window_title) of current foreground application.
    Returns (None, None) if no window is active, detection fails, or screen is idle.
    """
    if sys.platform == "win32":
        return _get_active_windows()
    elif sys.platform.startswith("linux"):
        return _get_active_linux()
    else:
        logger.debug("Unsupported platform: %s", sys.platform)
        return None, None
