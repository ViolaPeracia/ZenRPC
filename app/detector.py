import json
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


def is_wayland():
    """Returns True if running in a Wayland session, False otherwise."""
    return bool(
        os.environ.get("WAYLAND_DISPLAY")
        or os.environ.get("XDG_SESSION_TYPE") == "wayland"
    )


def _run_cmd(cmd, timeout=2):
    """Executes a command with strict timeout and captures stdout."""
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=timeout)
        return res.decode(errors="ignore").strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return ""
    except FileNotFoundError:
        global _LINUX_TOOLS_WARNED
        if not _LINUX_TOOLS_WARNED and (cmd and cmd[0] == "xdotool"):
            tool_name = cmd[0] if cmd else "command"
            logger.warning("Required tool '%s' not found on system PATH.", tool_name)
            _LINUX_TOOLS_WARNED = True
        return ""
    except Exception as e:
        logger.debug("Command %s failed: %s", cmd, e)
        return ""


def _get_linux_process_name(pid):
    """Directly reads /proc/<pid>/cmdline or /proc/<pid>/comm without spawning cat."""
    if pid is None or isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return None

    # First attempt: cmdline gives full, non-truncated binary name
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
        if raw:
            for part in raw.split(b"\x00"):
                if part:
                    arg = part.decode(errors="ignore")
                    name = os.path.basename(arg).strip()
                    if name:
                        return name.lower()
    except Exception as e:
        logger.debug("Failed reading /proc/%s/cmdline: %s", pid, e)

    # Fallback attempt: comm
    try:
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8", errors="ignore") as f:
            comm = f.read().strip()
            if comm:
                return comm.lower()
    except Exception as e:
        logger.debug("Failed reading /proc/%s/comm: %s", pid, e)

    return None


def _get_active_niri(timeout=1):
    """
    Detects the active/focused window on Niri Wayland compositor using:
    niri msg --json focused-window
    Returns (process_name, window_title) or (None, None).
    """
    raw_json = _run_cmd(["niri", "msg", "--json", "focused-window"], timeout=timeout)
    if not raw_json:
        return None, None

    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, Exception) as e:
        logger.debug("Failed to parse Niri JSON output: %s", e)
        return None, None

    if not isinstance(data, dict):
        return None, None

    pid = data.get("pid")
    app_id = data.get("app_id")
    raw_title = data.get("title")

    proc_name = None
    if isinstance(pid, int) and pid > 0:
        proc_name = _get_linux_process_name(pid)

    # If Niri reports the XWayland server/bridge process itself,
    # delegate to xdotool to resolve the real X11 client window and PID.
    if proc_name in ("xwayland", "xwayland-satellite"):
        return None, None

    if not proc_name and app_id and isinstance(app_id, str):
        clean_app = app_id.strip().lower()
        if clean_app:
            proc_name = clean_app

    if not proc_name:
        return None, None

    title = str(raw_title).strip() if raw_title else ""
    return proc_name, title


def _get_active_linux():
    """
    Detects active window on Linux.
    Prioritizes Niri native Wayland IPC if running in a Wayland session.
    Falls back to X11 / XWayland via xdotool.
    On pure Wayland sessions where neither succeeds, gracefully returns (None, None).
    """
    if is_wayland():
        niri_proc, niri_title = _get_active_niri()
        if niri_proc:
            return niri_proc, niri_title

    win_id = _run_cmd(["xdotool", "getactivewindow"], timeout=2)
    if not win_id or not win_id.isdigit() or int(win_id) <= 0:
        if is_wayland():
            logger.debug(
                "Wayland session detected and no active X11/XWayland window found; falling back to idle."
            )
        return None, None

    title = _run_cmd(["xdotool", "getwindowname", win_id], timeout=2)
    pid_str = _run_cmd(["xdotool", "getwindowpid", win_id], timeout=2)

    if not pid_str or not pid_str.isdigit() or int(pid_str) <= 0:
        return None, None

    proc_name = _get_linux_process_name(int(pid_str))
    if not proc_name:
        return None, None

    return proc_name, (title.strip() if title else "")


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
