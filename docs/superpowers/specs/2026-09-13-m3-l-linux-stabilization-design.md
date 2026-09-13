# M3-L Linux Stabilization Design Specification

- **Milestone:** M3-L — Linux Stabilization (Issues #9–#14)
- **Target Repository:** `githubuser2777/ZenRPC`
- **Date:** 2026-09-13
- **Status:** Proposed

---

## 1. Executive Summary & Goals

The M3-L milestone stabilizes ZenRPC on Linux systems across X11 and XWayland environments while cleanly establishing the Wayland boundary. This specification ensures:
1. Hardened Linux process and active-window detection in `app/detector.py`.
2. 100% offline subprocess safety unit tests in `tests/test_linux_detector.py` covering all failure modes (timeouts, non-zero exits, missing executables, malformed outputs, disappearing processes, permission denials, and Unicode).
3. A robust, CWD-independent Linux launcher (`run.sh` and updated `zenrpc.desktop`).
4. Explicit Wayland detection and graceful idle fallback without compositor IPC.
5. Real runtime verification on Linux X11/XWayland and full test suite passing.
6. Accurate updates to `README.md` and `docs/ROADMAP.md` reflecting verified capabilities.

---

## 2. Component Design & Changes

### 2.1 Linux Process Detection Hardening (`app/detector.py`)

#### A. Command Execution Safety (`_run_cmd`)
- Executes command with strict timeout (`timeout=2`).
- Catches:
  - `subprocess.TimeoutExpired`: returns `""`
  - `subprocess.CalledProcessError`: returns `""`
  - `FileNotFoundError`: logs single warning if tool is missing (`_LINUX_TOOLS_WARNED`), returns `""`
  - Any unexpected `Exception`: logs debug message, returns `""`
- Ensures outputs are cleanly decoded (ignoring invalid byte sequences) and stripped.

#### B. Process Name Extraction (`_get_linux_process_name(pid)`)
- Validates PID: if `pid is None` or `pid <= 0` or not `int`, returns `None`.
- Primary read (`/proc/<pid>/cmdline`):
  - Read binary raw bytes directly (`open(..., "rb")`).
  - Catches `ProcessLookupError`, `FileNotFoundError`, `PermissionError`, `OSError`.
  - Splitting by null bytes `b"\x00"`:
    - Finds the first non-empty argument.
    - Decodes with `errors="ignore"`.
    - Takes `os.path.basename(...)`.
    - Strips whitespace.
    - If valid and non-empty, returns lowercased name.
- Secondary fallback (`/proc/<pid>/comm`):
  - Used if `cmdline` is missing, empty (e.g. kernel threads, zombies), or yields an empty name.
  - Read as UTF-8 string with `errors="ignore"`.
  - Strips whitespace/newlines.
  - If valid and non-empty, returns lowercased name.
- If both attempts fail to produce a non-empty name, returns `None` (indicates process cannot be resolved, treated as no active process).

#### C. Active Window Detection (`_get_active_linux()`)
- Calls `_run_cmd(["xdotool", "getactivewindow"], timeout=2)`.
- If `win_id` is empty or not numeric/valid:
  - Returns `None, None`.
- Queries window title: `_run_cmd(["xdotool", "getwindowname", win_id], timeout=2)`.
  - If title query fails or times out, safely falls back to `""` (empty string).
  - Preserves full Unicode / multi-byte characters.
- Queries window PID: `_run_cmd(["xdotool", "getwindowpid", win_id], timeout=2)`.
  - If PID is empty, not digits, or `int(pid_str) <= 0`: returns `None, None`.
  - Resolves process name via `_get_linux_process_name(int(pid_str))`.
  - If process name is `None` or empty: returns `None, None`.
- Returns `(proc_name, title)`.

#### D. Wayland Detection & Fallback (`is_wayland()`)
- Helper `is_wayland()`:
  - Checks `bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland")`.
- In `_get_active_linux()`:
  - If `xdotool` fails or returns empty under Wayland, logs at debug level:
    `"Wayland session detected and no active X11/XWayland window found; falling back to idle."`
  - Returns `None, None`.
  - Does NOT crash, hang, or spawn compositor IPC.

---

### 2.2 Linux Subprocess Safety Unit Tests (`tests/test_linux_detector.py`)

A comprehensive offline test suite mirroring `tests/test_detector.py`:
1. `test_linux_valid_active_window`: Valid `win_id`, valid title, valid PID, valid `/proc/<pid>/cmdline`.
2. `test_linux_xdotool_timeout`: `xdotool getactivewindow` times out -> returns `(None, None)`.
3. `test_linux_xdotool_nonzero_exit`: `xdotool` exits with code 1 (no window focused) -> returns `(None, None)`.
4. `test_linux_xdotool_missing_binary`: `FileNotFoundError` when `xdotool` is absent -> returns `(None, None)` without throwing.
5. `test_linux_xdotool_malformed_output`: Empty, whitespace, or invalid window ID -> returns `(None, None)`.
6. `test_linux_missing_or_invalid_pid`: `getwindowpid` returns non-digit, empty, negative, or 0 -> returns `(None, None)`.
7. `test_linux_proc_disappears`: Process terminates after PID lookup (`FileNotFoundError`/`ProcessLookupError` on `/proc/<pid>`) -> returns `(None, None)`.
8. `test_linux_proc_permission_denied`: `/proc/<pid>/cmdline` raises `PermissionError` -> returns `(None, None)`.
9. `test_linux_proc_cmdline_empty_fallback_comm`: `/proc/<pid>/cmdline` is empty, fallback to `/proc/<pid>/comm` succeeds -> returns correct process name.
10. `test_linux_proc_cmdline_and_comm_empty`: Both cmdline and comm empty -> returns `(None, None)`.
11. `test_linux_cmdline_with_args_and_slashes`: `/usr/bin/google-chrome-stable\x00--no-sandbox` -> extracts `google-chrome-stable`.
12. `test_linux_unicode_window_title`: Multi-byte UTF-8 window titles (e.g. Vietnamese, CJK, Emojis) are preserved intact.
13. `test_linux_empty_window_title`: Empty window title returns empty string `""` without crashing.
14. `test_linux_wayland_idle_fallback`: When running in Wayland environment and active window query returns empty -> returns `(None, None)`.
15. `test_linux_presence_integration_recognized`: End-to-end integration test with `PresenceEngine` matching Linux app catalog (e.g. `gimp`, `vlc`, `code`).
16. `test_linux_presence_integration_unrecognized`: End-to-end integration test with `PresenceEngine` falling back to `Using <proc>`.

All tests run offline with zero dependencies on a real X server, Discord, or GUI.

---

### 2.3 Linux Launcher & Desktop Integration (`run.sh`, `zenrpc.desktop`)

#### A. Launcher Script (`run.sh`)
- Executable bash script in repo root.
- CWD-independent:
  ```bash
  #!/usr/bin/env bash
  APP_DIR="$(cd "$(dirname "$0")" && pwd)"
  if [ -x "$APP_DIR/.venv/bin/python" ]; then
      PYTHON="$APP_DIR/.venv/bin/python"
  elif command -v python3 &>/dev/null; then
      PYTHON="python3"
  else
      echo "Error: Python 3 not found." >&2
      exit 1
  fi
  exec "$PYTHON" "$APP_DIR/main.py" "$@"
  ```
- Works whether invoked as `./run.sh`, `bash /path/to/run.sh`, or from any current working directory.
- `main.py` already resolves configuration relative to `app/config.py` (`get_config_path()`), guaranteeing CWD independence.

#### B. Desktop Entry (`zenrpc.desktop`)
- Update `zenrpc.desktop`:
  - Provide clear `Exec=` and optional `Path=` instructions or portable script launcher reference.
  - Verify syntax using `desktop-file-validate` if available.

---

### 2.4 Wayland Boundary Definition (Issue #13)
- Explicitly documented:
  - Supported: X11 and XWayland (applications running under XWayland).
  - Graceful Fallback: Pure Wayland sessions without XWayland active-window support degrade cleanly to idle presence without crashes or hangs.
  - Out of Scope for M3-L: Native Wayland compositor IPC (Hyprland, Sway, Niri) is reserved for future Milestone M4.

---

### 2.5 Verification & Acceptance Baseline (Issue #14)
- Run full pytest suite across all test files.
- Execute real Linux runtime verification on the host machine:
  - Create X11 test window via `python-xlib` on DISPLAY=:1.
  - Verify active window detection, window title handling, process resolution.
  - Verify application switching resets timer.
  - Verify title changes preserve timer.
  - Verify process exit/closure transitions to idle.
  - Verify lock mode.
  - Verify config reload.
  - Verify clean startup and shutdown via signal (`SIGINT`/`SIGTERM`).
- Update `README.md` and `docs/ROADMAP.md` checking off Issues #9–#14.
