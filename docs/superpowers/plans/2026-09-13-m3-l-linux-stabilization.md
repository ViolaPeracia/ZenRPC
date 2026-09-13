# M3-L Linux Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete M3-L Linux stabilization milestone for `githubuser2777/ZenRPC` covering Issues #9–#14, including hardened Linux process detection, comprehensive offline subprocess unit tests, a CWD-independent launcher, explicit Wayland idle fallback, real X11/XWayland runtime verification, and updated documentation.

**Architecture:** Harden `app/detector.py` for Linux `/proc` and `xdotool` operations with strict 2s timeouts, process disappearance handling, and permission guards. Provide 100% offline tests in `tests/test_linux_detector.py` with mock subprocess and `/proc` fixtures. Add root `run.sh` launcher preserving script-relative paths. Run real Linux X11/XWayland runtime verification on DISPLAY=:1, and update `docs/ROADMAP.md` and `README.md`.

**Tech Stack:** Python 3, `xdotool`, Linux `/proc` filesystem, pytest, mock/monkeypatch.

**Spec:** `docs/superpowers/specs/2026-09-13-m3-l-linux-stabilization-design.md`

## Global Constraints

- Keep Python as the implementation language.
- Preserve existing Windows Win32 implementation and behavior unchanged.
- Use a single default 2-second timeout in `_run_cmd()`.
- If `/proc/<pid>/cmdline` fails or is unreadable, still try `/proc/<pid>/comm` before returning `None`.
- Keep XWayland working whenever `xdotool` can successfully detect an active window, even inside a Wayland session.
- Gracefully degrade to idle `(None, None)` when generic Wayland window inspection is unavailable.
- Do NOT implement compositor-specific Wayland IPC (Hyprland/Sway/Niri) in M3-L.
- Keep PresenceEngine integration tests fully offline by mocking detector output.
- `python-xlib` is verification-only and must not become a runtime dependency in `requirements.txt`.
- No GUI, database, cloud sync, telemetry, plugin system, Electron, Qt, or external daemons.
- Preserve the existing 128 UTF-8 byte safety limit.

---

### Task 1: Harden Linux Process Detection and Wayland Boundary in `app/detector.py` (Issues #10 & #13)

**Files:**
- Modify: `app/detector.py:91-168`
- Test: `tests/test_linux_detector.py`

**Interfaces:**
- Consumes: `os.environ`, `/proc/<pid>/cmdline`, `/proc/<pid>/comm`, `subprocess.check_output`
- Produces:
  - `is_wayland() -> bool`: Returns `True` if Wayland session detected.
  - `_get_linux_process_name(pid: int) -> str | None`: Returns lowercased process name or `None`.
  - `_get_active_linux() -> tuple[str | None, str | None]`: Returns `(process_name, window_title)` or `(None, None)`.
  - `get_active_window_info() -> tuple[str | None, str | None]`: Cross-platform entry point returning `(process_name, window_title)` or `(None, None)`.

- [ ] **Step 1: Write failing unit test for `is_wayland`, `_get_linux_process_name`, and `_get_active_linux`**

Write initial tests in `tests/test_linux_detector.py` testing:
1. `is_wayland()` returns True when `WAYLAND_DISPLAY` or `XDG_SESSION_TYPE=wayland` is set.
2. `_get_linux_process_name(pid)` returns `None` for non-positive or invalid PIDs.
3. `_get_linux_process_name(pid)` falls back to `/proc/<pid>/comm` if `/proc/<pid>/cmdline` is empty or raises OSError.
4. `_get_active_linux()` returns `(None, None)` if `xdotool getactivewindow` returns empty, and handles Wayland logging cleanly.

```python
import os
import subprocess
from unittest.mock import patch, mock_open
import pytest
from app import detector

def test_is_wayland(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    assert detector.is_wayland() is False

    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    assert detector.is_wayland() is True

    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert detector.is_wayland() is True

def test_get_linux_process_name_invalid_pid():
    assert detector._get_linux_process_name(0) is None
    assert detector._get_linux_process_name(-1) is None
    assert detector._get_linux_process_name(None) is None
    assert detector._get_linux_process_name("abc") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_linux_detector.py -v`
Expected: FAIL (missing `is_wayland` or returning `"unknown"` instead of `None`).

- [ ] **Step 3: Implement minimal changes in `app/detector.py`**

Update `app/detector.py`:
- Add `is_wayland()` function.
- Update `_run_cmd(cmd, timeout=2)` with a single default strict timeout of 2 seconds.
- Harden `_get_linux_process_name(pid)`:
  - Return `None` if `pid is None or not isinstance(pid, int) or pid <= 0`.
  - Try `/proc/<pid>/cmdline` first (read binary, split by null, extract first non-empty arg, `os.path.basename`, strip).
  - If cmdline is empty, unreadable, or yields empty string, fall back to `/proc/<pid>/comm`.
  - If both fail, return `None`.
- Update `_get_active_linux()`:
  - Query `win_id`. If empty:
    - If `is_wayland()`: log debug message regarding Wayland session and no active X11/XWayland window.
    - Return `None, None`.
  - Query `title`: default to `""` if empty or failed.
  - Query `pid_str`: if empty or not `pid_str.isdigit()` or `int(pid_str) <= 0`: return `None, None`.
  - Resolve `proc_name = _get_linux_process_name(int(pid_str))`.
  - If `proc_name` is `None` or empty: return `None, None`.
  - Return `proc_name, title`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_linux_detector.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/detector.py tests/test_linux_detector.py
git commit -m "feat(detector): harden Linux process detection and add Wayland boundary (Issues #10, #13)"
```

---

### Task 2: Comprehensive Offline Linux Subprocess Safety Tests (Issue #11)

**Files:**
- Create/Modify: `tests/test_linux_detector.py`
- Modify: `app/detector.py` (if any edge case fixes needed)

**Interfaces:**
- Consumes: `app.detector.get_active_window_info`, `app.detector._run_cmd`, `app.detector._get_linux_process_name`
- Produces: Full offline pytest suite verifying:
  - `xdotool` timeout expired (`subprocess.TimeoutExpired`)
  - `xdotool` non-zero exit code (`subprocess.CalledProcessError`)
  - `xdotool` missing executable (`FileNotFoundError`)
  - `xdotool` malformed output (whitespace, non-numeric)
  - PID lookup failures (empty, non-digit, negative, 0)
  - Process disappearing between PID lookup and `/proc` read
  - Permission denied on `/proc/<pid>` (`PermissionError`)
  - Malformed `/proc/<pid>/cmdline` with null bytes and spaces
  - `/proc/<pid>/comm` fallback when cmdline empty
  - Unicode multi-byte window titles
  - Empty window title
  - Offline integration with `PresenceEngine`

- [ ] **Step 1: Write offline test suite in `tests/test_linux_detector.py`**

Write tests covering:
1. `test_run_cmd_timeout`: simulates `TimeoutExpired`.
2. `test_run_cmd_called_process_error`: simulates exit code 1.
3. `test_run_cmd_file_not_found`: simulates `FileNotFoundError` and verifies single warning.
4. `test_linux_valid_active_window`: mocked `xdotool` and `/proc` returning valid `code`, `workspace - Visual Studio Code`.
5. `test_linux_active_window_none_or_empty`: `getactivewindow` returns empty string.
6. `test_linux_window_pid_invalid_or_missing`: `getwindowpid` returns `""` or `"invalid"`.
7. `test_linux_process_disappears_before_proc_read`: `/proc/<pid>/cmdline` raises `FileNotFoundError`.
8. `test_linux_proc_permission_denied`: `/proc/<pid>/cmdline` raises `PermissionError`.
9. `test_linux_proc_cmdline_empty_comm_success`: cmdline is `b""`, comm is `spotify`.
10. `test_linux_proc_cmdline_and_comm_empty`: both return empty -> returns `(None, None)`.
11. `test_linux_proc_cmdline_with_args_and_slashes`: `/usr/bin/google-chrome-stable\x00--flag` -> `google-chrome-stable`.
12. `test_linux_unicode_window_title`: multi-byte title like `Dự án ZenRPC 🚀` is preserved.
13. `test_linux_empty_window_title`: empty title returns `(proc_name, "")`.
14. `test_linux_wayland_degradation_to_idle`: Wayland session without active X11 window returns `(None, None)`.
15. `test_linux_presence_integration_recognized`: mocked detector fed into `PresenceEngine` matching catalog.
16. `test_linux_presence_integration_unrecognized`: mocked detector fed into `PresenceEngine` falling back to `Using <proc>`.

- [ ] **Step 2: Run tests to verify all tests pass**

Run: `.venv/bin/pytest tests/test_linux_detector.py -v`
Expected: PASS (all 16+ tests pass offline without X11 or Discord).

- [ ] **Step 3: Run full test suite across entire repository**

Run: `.venv/bin/pytest -v`
Expected: 52+ tests pass (36 existing + 16+ new Linux tests).

- [ ] **Step 4: Commit**

```bash
git add tests/test_linux_detector.py
git commit -m "test(linux): add comprehensive offline Linux subprocess safety tests (Issue #11)"
```

---

### Task 3: Linux Launcher and CWD Independence (Issue #12)

**Files:**
- Create: `run.sh`
- Modify: `zenrpc.desktop`
- Modify: `install.sh`
- Test: `tests/test_config.py` (verify launcher CWD independence test)

**Interfaces:**
- Consumes: bash, python environment
- Produces:
  - `run.sh`: executable launcher script running from any current working directory.
  - `zenrpc.desktop`: desktop entry configuration.

- [ ] **Step 1: Create `run.sh`**

Implement `run.sh`:
```bash
#!/usr/bin/env bash
set -e

# Resolve repository root directory regardless of current working directory
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -x "$APP_DIR/.venv/bin/python" ]; then
    PYTHON="$APP_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "[!] Python 3 not found." >&2
    exit 1
fi

exec "$PYTHON" "$APP_DIR/main.py" "$@"
```
Make `run.sh` executable: `chmod +x run.sh`.

- [ ] **Step 2: Update `zenrpc.desktop`**

Configure `zenrpc.desktop` with `Path=` and `Exec=` targeting `run.sh` or python with main.py:
```ini
[Desktop Entry]
Type=Application
Name=ZenRPC
Comment=Discord Rich Presence for active window
Exec=sh -c '"$(dirname "%k")"/run.sh'
Icon=discord
Terminal=false
Categories=Utility;
StartupNotify=false
```

- [ ] **Step 3: Update `install.sh` to ensure `run.sh` is executable**

Ensure `chmod +x run.sh` is in `install.sh`.

- [ ] **Step 4: Verify CWD independence of `run.sh`**

Test running `run.sh` from `/tmp`:
Run: `(cd /tmp && /home/skids/orca/ZenRPC/run.sh --help || true)` (or verify with python -c inspecting paths).
Add a test in `tests/test_config.py` verifying that running `run.sh` or invoking `main.py` from any CWD correctly resolves `config.json` relative to script directory.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/pytest -v`
Expected: PASS.
```bash
git add run.sh zenrpc.desktop install.sh tests/test_config.py
git commit -m "feat(launcher): add CWD-independent Linux launcher and update desktop entry (Issue #12)"
```

---

### Task 4: Real Linux X11/XWayland Runtime Verification (Issue #9)

**Files:**
- Create: `tests/verify_linux_runtime.py` (verification harness using `python-xlib` on DISPLAY=:1)
- Verify live behavior:
  - Foreground-window detection on Linux XWayland (`DISPLAY=:1`).
  - 2-second timeout enforcement.
  - PID/process resolution and window-title handling.
  - Recognized app matching and unrecognized app fallback.
  - App switching resets elapsed timer.
  - Title-only change preserves elapsed timer.
  - Window closure/exit triggers idle clearing.
  - Clean shutdown on SIGINT/SIGTERM.

- [ ] **Step 1: Write runtime verification harness script `tests/verify_linux_runtime.py`**

The script runs against the live XWayland display:
1. Creates Window A with title `"VS Code Window"`, mapped and focused. Verifies detector returns `('python', 'VS Code Window')`.
2. Verifies PresenceEngine connects (with mock RPC) and records start timestamp.
3. Updates Window A title to `"VS Code Window - modified"`. Verifies timer is preserved.
4. Creates Window B with title `"Browser Window"` and different process/name simulation. Verifies timer resets.
5. Closes windows, unmaps. Verifies detector returns `(None, None)` and presence clears on idle.
6. Verifies engine stop and clean exit.

- [ ] **Step 2: Run verification harness**

Run: `.venv/bin/python tests/verify_linux_runtime.py`
Expected: PASS with all assertion checks logged.

- [ ] **Step 3: Commit verification harness**

```bash
git add tests/verify_linux_runtime.py
git commit -m "test(linux): add real Linux X11/XWayland runtime verification harness (Issue #9)"
```

---

### Task 5: Linux Release Baseline Verification & Documentation (Issue #14)

**Files:**
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/DEVELOPMENT.md`

- [ ] **Step 1: Run complete test suite and record exact test count and result**

Run: `.venv/bin/pytest -v`
Expected: All tests passing (100% pass rate).

- [ ] **Step 2: Update `docs/ROADMAP.md`**
- Check off Issues #9, #10, #11, #12, #13, #14 under `M3-L — Linux Stabilization`.
- Move `M3-L` to Completed Milestones section.
- Update test count in Section 6 to reflect the exact new test count (e.g., 52+ tests).
- Document verified Linux runtime baseline and Wayland boundary.

- [ ] **Step 3: Update `README.md` and `docs/DEVELOPMENT.md`**
- Update Linux instructions to mention `run.sh`, `install.sh`, and `xdotool` dependency.
- Document Wayland fallback and X11/XWayland support.
- Ensure test count references are accurate.

- [ ] **Step 4: Final verification and commit**

Run: `.venv/bin/pytest -v`
Run: `git status`
```bash
git add README.md docs/ROADMAP.md docs/DEVELOPMENT.md
git commit -m "docs: complete M3-L Linux stabilization milestone and release baseline (Issue #14)"
```
