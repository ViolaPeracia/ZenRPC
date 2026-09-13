import io
import os
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from app import detector
from app.presence import PresenceEngine


# ============================================================================
# Environment and helper tests
# ============================================================================


def test_is_wayland(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    assert detector.is_wayland() is False

    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    assert detector.is_wayland() is True

    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert detector.is_wayland() is True

    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert detector.is_wayland() is False


def test_get_linux_process_name_invalid_pid():
    assert detector._get_linux_process_name(0) is None
    assert detector._get_linux_process_name(-1) is None
    assert detector._get_linux_process_name(None) is None
    assert detector._get_linux_process_name("abc") is None
    assert detector._get_linux_process_name(True) is None


# ============================================================================
# Subprocess / Command Execution Safety Tests (_run_cmd)
# ============================================================================


def test_run_cmd_timeout():
    """Simulates TimeoutExpired in _run_cmd and verifies safe fallback to empty string."""
    with patch("subprocess.check_output", side_effect=subprocess.TimeoutExpired(cmd=["xdotool"], timeout=2)):
        assert detector._run_cmd(["xdotool", "getactivewindow"]) == ""


def test_run_cmd_called_process_error():
    """Simulates CalledProcessError (exit code != 0) in _run_cmd and verifies safe fallback."""
    with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(returncode=1, cmd=["xdotool"])):
        assert detector._run_cmd(["xdotool", "getactivewindow"]) == ""


def test_run_cmd_file_not_found(monkeypatch):
    """Simulates FileNotFoundError in _run_cmd and verifies single warning behavior."""
    monkeypatch.setattr(detector, "_LINUX_TOOLS_WARNED", False)
    with patch("subprocess.check_output", side_effect=FileNotFoundError("Tool not found")):
        with patch.object(detector.logger, "warning") as mock_warn:
            # First call triggers warning
            res1 = detector._run_cmd(["xdotool", "getactivewindow"])
            assert res1 == ""
            mock_warn.assert_called_once_with(
                "Required tool '%s' not found on system PATH.", "xdotool"
            )

            # Second call does not warn again (single warning behavior)
            res2 = detector._run_cmd(["xdotool", "getwindowname", "123"])
            assert res2 == ""
            assert mock_warn.call_count == 1


def test_run_cmd_generic_exception():
    """Simulates unexpected Exception in _run_cmd and verifies safe fallback."""
    with patch("subprocess.check_output", side_effect=RuntimeError("Subprocess execution failed")):
        assert detector._run_cmd(["xdotool", "getactivewindow"]) == ""


# ============================================================================
# Linux Active Window Detection Tests (_get_active_linux)
# ============================================================================


def test_linux_valid_active_window():
    """Simulates valid active window detection via xdotool and /proc/pid/cmdline."""
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "123456"
        elif "getwindowname" in cmd:
            return "workspace - Visual Studio Code"
        elif "getwindowpid" in cmd:
            return "7890"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", return_value=io.BytesIO(b"/usr/share/code/code\x00/workspace\x00")):
            proc, title = detector._get_active_linux()
            assert proc == "code"
            assert title == "workspace - Visual Studio Code"


@pytest.mark.parametrize("win_id_output", ["", "   ", "\n", "0", "-1", "none", "xyz"])
def test_linux_active_window_none_or_empty(win_id_output):
    """Simulates xdotool getactivewindow returning empty, whitespace, 0, or non-numeric output."""
    with patch.object(detector, "_run_cmd", return_value=win_id_output):
        proc, title = detector._get_active_linux()
        assert proc is None
        assert title is None


@pytest.mark.parametrize("pid_output", ["", "   ", "invalid", "-1", "0", "abc"])
def test_linux_window_pid_invalid_or_missing(pid_output):
    """Simulates xdotool getwindowpid returning empty, invalid, 0, or negative PID."""
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "12345"
        elif "getwindowname" in cmd:
            return "Some App"
        elif "getwindowpid" in cmd:
            return pid_output
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        proc, title = detector._get_active_linux()
        assert proc is None
        assert title is None


def test_linux_process_disappears_before_proc_read():
    """Simulates process terminating between PID lookup and /proc read (FileNotFoundError/ProcessLookupError)."""
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "12345"
        elif "getwindowname" in cmd:
            return "Terminating Process Window"
        elif "getwindowpid" in cmd:
            return "4321"
        return ""

    # Direct function test with FileNotFoundError
    with patch("builtins.open", side_effect=FileNotFoundError("No such process")):
        assert detector._get_linux_process_name(4321) is None

    # Direct function test with ProcessLookupError
    with patch("builtins.open", side_effect=ProcessLookupError("Process lookup failed")):
        assert detector._get_linux_process_name(4321) is None

    # Full _get_active_linux integration
    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", side_effect=FileNotFoundError("No such process")):
            proc, title = detector._get_active_linux()
            assert proc is None
            assert title is None


def test_linux_proc_permission_denied():
    """Simulates PermissionError on /proc/<pid> (e.g. root or other user process)."""
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "12345"
        elif "getwindowname" in cmd:
            return "Root Process Window"
        elif "getwindowpid" in cmd:
            return "1"
        return ""

    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        assert detector._get_linux_process_name(1) is None

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            proc, title = detector._get_active_linux()
            assert proc is None
            assert title is None


def test_linux_proc_cmdline_empty_comm_success():
    """Simulates empty /proc/<pid>/cmdline falling back successfully to /proc/<pid>/comm."""
    def mock_open_proc(path, *args, **kwargs):
        if path == "/proc/1234/cmdline":
            return io.BytesIO(b"")
        elif path == "/proc/1234/comm":
            return io.StringIO("spotify\n")
        raise FileNotFoundError(path)

    with patch("builtins.open", side_effect=mock_open_proc):
        assert detector._get_linux_process_name(1234) == "spotify"

    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "555"
        elif "getwindowname" in cmd:
            return "Spotify Free"
        elif "getwindowpid" in cmd:
            return "1234"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", side_effect=mock_open_proc):
            proc, title = detector._get_active_linux()
            assert proc == "spotify"
            assert title == "Spotify Free"


def test_linux_proc_cmdline_and_comm_empty():
    """Simulates both /proc/<pid>/cmdline and /proc/<pid>/comm being empty -> returns (None, None)."""
    def mock_open_proc(path, *args, **kwargs):
        if path == "/proc/1234/cmdline":
            return io.BytesIO(b"")
        elif path == "/proc/1234/comm":
            return io.StringIO("   \n")
        raise FileNotFoundError(path)

    with patch("builtins.open", side_effect=mock_open_proc):
        assert detector._get_linux_process_name(1234) is None

    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "555"
        elif "getwindowname" in cmd:
            return "Empty Window"
        elif "getwindowpid" in cmd:
            return "1234"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", side_effect=mock_open_proc):
            proc, title = detector._get_active_linux()
            assert proc is None
            assert title is None


def test_linux_proc_cmdline_with_args_and_slashes():
    """Verifies parsing cmdline containing paths, args, null bytes, and spaces."""
    test_cases = [
        (b"/usr/bin/google-chrome-stable\x00--flag\x00--type=zygote", "google-chrome-stable"),
        (b"/opt/my tools/custom_app\x00--config=/etc/conf\x00", "custom_app"),
        (b"\x00\x00/usr/local/bin/editor\x00", "editor"),
        (b"simple_binary\x00arg1\x00", "simple_binary"),
    ]
    for raw_bytes, expected_name in test_cases:
        with patch("builtins.open", return_value=io.BytesIO(raw_bytes)):
            assert detector._get_linux_process_name(9999) == expected_name


def test_linux_unicode_window_title():
    """Verifies multi-byte Unicode window titles (Vietnamese, emojis, CJK) are preserved."""
    unicode_title = "Dự án ZenRPC 🚀 — Chạy thử nghiệm 2026 (漢字)"

    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "12345"
        elif "getwindowname" in cmd:
            return unicode_title
        elif "getwindowpid" in cmd:
            return "7890"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", return_value=io.BytesIO(b"/usr/bin/orca-ide\x00")):
            proc, title = detector._get_active_linux()
            assert proc == "orca-ide"
            assert title == unicode_title


def test_linux_empty_window_title():
    """Verifies empty or whitespace-only window titles return (proc_name, "")."""
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "12345"
        elif "getwindowname" in cmd:
            return ""
        elif "getwindowpid" in cmd:
            return "7890"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch("builtins.open", return_value=io.BytesIO(b"/usr/bin/code\x00")):
            proc, title = detector._get_active_linux()
            assert proc == "code"
            assert title == ""

    # Whitespace-only window title is stripped by _run_cmd to empty string
    def fake_run_cmd_whitespace(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "12345"
        elif "getwindowname" in cmd:
            return "   \t  "
        elif "getwindowpid" in cmd:
            return "7890"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd_whitespace):
        with patch("builtins.open", return_value=io.BytesIO(b"/usr/bin/code\x00")):
            proc, title = detector._get_active_linux()
            assert proc == "code"
            assert title == ""


def test_linux_wayland_degradation_to_idle(monkeypatch):
    """Verifies graceful degradation to idle on Wayland when no active X11 window is found."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    with patch.object(detector, "_run_cmd", return_value=""):
        with patch.object(detector.logger, "debug") as mock_debug:
            proc, title = detector._get_active_linux()
            assert proc is None
            assert title is None
            mock_debug.assert_any_call(
                "Wayland session detected and no active X11/XWayland window found; falling back to idle."
            )


# ============================================================================
# Public API & Integration Tests
# ============================================================================


def test_get_active_window_info_linux(monkeypatch):
    """Verifies public get_active_window_info() delegates to _get_active_linux on Linux."""
    monkeypatch.setattr(detector.sys, "platform", "linux")
    with patch.object(detector, "_get_active_linux", return_value=("code", "ZenRPC - VS Code")) as mock_linux:
        result = detector.get_active_window_info()
        assert result == ("code", "ZenRPC - VS Code")
        mock_linux.assert_called_once()

    # Unsupported platform returns (None, None)
    monkeypatch.setattr(detector.sys, "platform", "darwin")
    assert detector.get_active_window_info() == (None, None)


def test_linux_presence_integration_recognized(mock_rpc_factory, tmp_path, monkeypatch):
    """Offline PresenceEngine integration for recognized Linux application."""
    from app.config import save_config
    cfg_path = str(tmp_path / "config.json")
    save_config({"client_id": "123456789"}, cfg_path)

    monkeypatch.setattr(detector.sys, "platform", "linux")
    monkeypatch.setattr(detector, "_get_active_linux", lambda: ("code", "workspace - Visual Studio Code"))

    engine = PresenceEngine(
        config_path=cfg_path,
        detector_fn=detector.get_active_window_info,
        rpc_factory=mock_rpc_factory,
    )
    assert engine.connect() is True
    engine.update_once()

    rpc = mock_rpc_factory.instances[0]
    assert len(rpc.updates) == 1
    update = rpc.updates[0]
    assert update["large_image"] == "vscode"
    assert update["large_text"] == "Visual Studio Code"
    assert update["details"] == "Coding"
    assert update["state"] == "workspace - Visual Studio Code"


def test_linux_presence_integration_unrecognized(mock_rpc_factory, tmp_path, monkeypatch):
    """Offline PresenceEngine integration for unrecognized Linux application fallback."""
    from app.config import save_config
    cfg_path = str(tmp_path / "config.json")
    save_config({"client_id": "123456789"}, cfg_path)

    monkeypatch.setattr(detector.sys, "platform", "linux")
    monkeypatch.setattr(detector, "_get_active_linux", lambda: ("custom_linux_tool", "Diagram v1"))

    engine = PresenceEngine(
        config_path=cfg_path,
        detector_fn=detector.get_active_window_info,
        rpc_factory=mock_rpc_factory,
    )
    assert engine.connect() is True
    engine.update_once()

    rpc = mock_rpc_factory.instances[0]
    assert len(rpc.updates) == 1
    update = rpc.updates[0]
    assert "large_image" not in update
    assert update["details"] == "Using custom_linux_tool"
    assert update["state"] == "Diagram v1"
