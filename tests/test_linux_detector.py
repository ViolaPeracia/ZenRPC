import io
import os
import subprocess
from unittest.mock import patch, MagicMock
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

    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert detector.is_wayland() is False


def test_get_linux_process_name_invalid_pid():
    assert detector._get_linux_process_name(0) is None
    assert detector._get_linux_process_name(-1) is None
    assert detector._get_linux_process_name(None) is None
    assert detector._get_linux_process_name("abc") is None
    assert detector._get_linux_process_name(True) is None


def test_get_linux_process_name_cmdline_success():
    with patch("builtins.open", return_value=io.BytesIO(b"/usr/bin/google-chrome-stable\x00--no-sandbox\x00")):
        assert detector._get_linux_process_name(1234) == "google-chrome-stable"


def test_get_linux_process_name_fallback_comm_on_oserror():
    def mock_open_proc(path, *args, **kwargs):
        if path == "/proc/1234/cmdline":
            raise OSError("Unreadable")
        elif path == "/proc/1234/comm":
            return io.StringIO("kworker/u16:0\n")
        raise FileNotFoundError(path)

    with patch("builtins.open", side_effect=mock_open_proc):
        assert detector._get_linux_process_name(1234) == "kworker/u16:0"


def test_get_linux_process_name_fallback_comm_on_empty_cmdline():
    def mock_open_proc(path, *args, **kwargs):
        if path == "/proc/1234/cmdline":
            return io.BytesIO(b"")
        elif path == "/proc/1234/comm":
            return io.StringIO("code\n")
        raise FileNotFoundError(path)

    with patch("builtins.open", side_effect=mock_open_proc):
        assert detector._get_linux_process_name(1234) == "code"


def test_get_linux_process_name_both_fail():
    with patch("builtins.open", side_effect=OSError("Process disappeared")):
        assert detector._get_linux_process_name(1234) is None


def test_get_active_linux_wayland_fallback(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    with patch.object(detector, "_run_cmd", return_value=""):
        with patch.object(detector.logger, "debug") as mock_debug:
            proc, title = detector._get_active_linux()
            assert proc is None
            assert title is None
            mock_debug.assert_any_call(
                "Wayland session detected and no active X11/XWayland window found; falling back to idle."
            )


def test_get_active_linux_success():
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "123456"
        elif "getwindowname" in cmd:
            return "Visual Studio Code"
        elif "getwindowpid" in cmd:
            return "7890"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch.object(detector, "_get_linux_process_name", return_value="code") as mock_proc:
            proc, title = detector._get_active_linux()
            assert proc == "code"
            assert title == "Visual Studio Code"
            mock_proc.assert_called_once_with(7890)


def test_get_active_linux_invalid_pid():
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "123456"
        elif "getwindowname" in cmd:
            return "Visual Studio Code"
        elif "getwindowpid" in cmd:
            return "not-a-pid"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        proc, title = detector._get_active_linux()
        assert proc is None
        assert title is None


def test_get_active_linux_process_name_none():
    def fake_run_cmd(cmd, timeout=2):
        if "getactivewindow" in cmd:
            return "123456"
        elif "getwindowname" in cmd:
            return "Visual Studio Code"
        elif "getwindowpid" in cmd:
            return "7890"
        return ""

    with patch.object(detector, "_run_cmd", side_effect=fake_run_cmd):
        with patch.object(detector, "_get_linux_process_name", return_value=None):
            proc, title = detector._get_active_linux()
            assert proc is None
            assert title is None
