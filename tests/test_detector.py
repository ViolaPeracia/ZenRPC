from unittest import mock
import pytest
from app import detector
from app.presence import PresenceEngine


class MockNoSuchProcess(Exception):
    pass


class MockAccessDenied(Exception):
    pass


class MockZombieProcess(Exception):
    pass


@pytest.fixture
def mock_win32_env(monkeypatch):
    """Sets up a complete set of mock win32 and psutil objects in app.detector."""
    mock_gui = mock.Mock()
    mock_proc = mock.Mock()
    mock_ps = mock.Mock()

    # Configure exception types
    mock_ps.NoSuchProcess = MockNoSuchProcess
    mock_ps.AccessDenied = MockAccessDenied
    mock_ps.ZombieProcess = MockZombieProcess

    # Default valid behavior
    mock_gui.GetForegroundWindow.return_value = 1001
    mock_gui.GetWindowText.return_value = "Project - Visual Studio Code"
    mock_proc.GetWindowThreadProcessId.return_value = (0, 4200)

    proc_instance = mock.Mock()
    proc_instance.is_running.return_value = True
    proc_instance.name.return_value = "Code.exe"
    mock_ps.Process.return_value = proc_instance

    monkeypatch.setattr(detector, "win32gui", mock_gui)
    monkeypatch.setattr(detector, "win32process", mock_proc)
    monkeypatch.setattr(detector, "psutil", mock_ps)
    monkeypatch.setattr(detector.sys, "platform", "win32")

    return {
        "gui": mock_gui,
        "proc": mock_proc,
        "psutil": mock_ps,
        "process_instance": proc_instance,
    }


def test_valid_foreground_window(mock_win32_env):
    """Case 1 & 2: Valid foreground HWND -> valid PID -> valid process name."""
    proc_name, title = detector.get_active_window_info()
    assert proc_name == "Code.exe"
    assert title == "Project - Visual Studio Code"

    mock_win32_env["gui"].GetForegroundWindow.assert_called_once()
    mock_win32_env["gui"].GetWindowText.assert_called_once_with(1001)
    mock_win32_env["proc"].GetWindowThreadProcessId.assert_called_once_with(1001)
    mock_win32_env["psutil"].Process.assert_called_once_with(4200)


def test_hwnd_zero(mock_win32_env):
    """Case 3: hwnd == 0 (no foreground window / desktop active)."""
    mock_win32_env["gui"].GetForegroundWindow.return_value = 0
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_hwnd_none(mock_win32_env):
    """Case 4: hwnd is None."""
    mock_win32_env["gui"].GetForegroundWindow.return_value = None
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_pid_invalid_or_nonpositive(mock_win32_env):
    """Case 5: pid <= 0 or None."""
    # pid == 0
    mock_win32_env["proc"].GetWindowThreadProcessId.return_value = (0, 0)
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None

    # pid == -1
    mock_win32_env["proc"].GetWindowThreadProcessId.return_value = (0, -1)
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None

    # pid is None
    mock_win32_env["proc"].GetWindowThreadProcessId.return_value = (0, None)
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_process_disappears_after_pid_lookup(mock_win32_env):
    """Case 6 & 7: Process terminates between PID lookup and psutil inspection (NoSuchProcess)."""
    mock_win32_env["psutil"].Process.side_effect = MockNoSuchProcess("PID disappeared")
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_psutil_access_denied(mock_win32_env):
    """Case 8: psutil.AccessDenied for privileged system processes."""
    mock_win32_env["psutil"].Process.side_effect = MockAccessDenied("Access denied")
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_psutil_zombie_process(mock_win32_env):
    """Case 9: psutil.ZombieProcess or process not running."""
    mock_win32_env["psutil"].Process.side_effect = MockZombieProcess("Zombie")
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None

    # proc.is_running() == False
    mock_win32_env["psutil"].Process.side_effect = None
    mock_win32_env["process_instance"].is_running.return_value = False
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_unexpected_win32_exception(mock_win32_env):
    """Case 10: Unexpected Win32 error in GetForegroundWindow or GetWindowThreadProcessId."""
    mock_win32_env["gui"].GetForegroundWindow.side_effect = RuntimeError("Win32 device error")
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None

    # Error during PID lookup
    mock_win32_env["gui"].GetForegroundWindow.side_effect = None
    mock_win32_env["gui"].GetForegroundWindow.return_value = 1001
    mock_win32_env["proc"].GetWindowThreadProcessId.side_effect = RuntimeError("Invalid HWND")
    proc_name, title = detector.get_active_window_info()
    assert proc_name is None
    assert title is None


def test_empty_process_name(mock_win32_env):
    """Case 11: Empty or whitespace-only process name returns (None, None)."""
    mock_win32_env["process_instance"].name.return_value = ""
    assert detector.get_active_window_info() == (None, None)

    mock_win32_env["process_instance"].name.return_value = "   "
    assert detector.get_active_window_info() == (None, None)

    mock_win32_env["process_instance"].name.return_value = None
    assert detector.get_active_window_info() == (None, None)


def test_empty_window_title(mock_win32_env):
    """Case 12: Empty title is safely preserved as empty string without crashing."""
    mock_win32_env["gui"].GetWindowText.return_value = ""
    proc_name, title = detector.get_active_window_info()
    assert proc_name == "Code.exe"
    assert title == ""

    # Exception in GetWindowText safely defaults to empty title
    mock_win32_env["gui"].GetWindowText.side_effect = RuntimeError("Text read error")
    proc_name, title = detector.get_active_window_info()
    assert proc_name == "Code.exe"
    assert title == ""


def test_whitespace_window_title(mock_win32_env):
    """Case 13: Whitespace-only window title is stripped to empty string."""
    mock_win32_env["gui"].GetWindowText.return_value = "   \t \n  "
    proc_name, title = detector.get_active_window_info()
    assert proc_name == "Code.exe"
    assert title == ""


def test_unicode_multibyte_window_title(mock_win32_env):
    """Case 14: Multi-byte Unicode window title (Vietnamese, emojis, CJK) is preserved."""
    unicode_title = "Dự án ZenRPC 🚀 — Chạy thử nghiệm 2026 (漢字)"
    mock_win32_env["gui"].GetWindowText.return_value = unicode_title
    proc_name, title = detector.get_active_window_info()
    assert proc_name == "Code.exe"
    assert title == unicode_title


def test_recognized_process_presence_mapping(mock_win32_env, mock_rpc_factory, tmp_path):
    """Case 15: Recognized process detected by Windows detector maps to asset key and display name."""
    from app.config import save_config
    cfg_path = str(tmp_path / "config.json")
    save_config({"client_id": "123456789"}, cfg_path)

    mock_win32_env["process_instance"].name.return_value = "chrome.exe"
    mock_win32_env["gui"].GetWindowText.return_value = "GitHub - ZenRPC"

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
    assert update["large_image"] == "chrome"
    assert update["large_text"] == "Google Chrome"
    assert update["details"] == "Browsing the web"
    assert update["state"] == "GitHub - ZenRPC"


def test_unrecognized_process_presence_fallback(mock_win32_env, mock_rpc_factory, tmp_path):
    """Case 16: Unrecognized process detected by Windows detector falls back gracefully."""
    from app.config import save_config
    cfg_path = str(tmp_path / "config.json")
    save_config({"client_id": "123456789"}, cfg_path)

    mock_win32_env["process_instance"].name.return_value = "proprietary_cad_tool.exe"
    mock_win32_env["gui"].GetWindowText.return_value = "Blueprint v1.0"

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
    assert update["details"] == "Using proprietary_cad_tool"
    assert update["state"] == "Blueprint v1.0"


def test_windows_terminal_dataflow_and_switch_behavior(mock_win32_env, mock_rpc_factory, tmp_path):
    """
    Verifies that Windows Terminal running a subshell (e.g. .venv\\Scripts\\pythonw.exe)
    is accurately detected as WindowsTerminal.exe with the tab title as state,
    and cleanly transitions when switching to another application and back.
    """
    from app.config import save_config
    cfg_path = str(tmp_path / "config.json")
    save_config({"client_id": "123456789"}, cfg_path)

    # 1. Start with Windows Terminal in foreground
    mock_win32_env["process_instance"].name.return_value = "WindowsTerminal.exe"
    mock_win32_env["gui"].GetWindowText.return_value = ".venv\\Scripts\\pythonw.exe"

    engine = PresenceEngine(
        config_path=cfg_path,
        detector_fn=detector.get_active_window_info,
        rpc_factory=mock_rpc_factory,
    )
    assert engine.connect() is True
    engine.update_once()

    rpc = mock_rpc_factory.instances[0]
    assert len(rpc.updates) == 1
    u1 = rpc.updates[0]
    assert u1["details"] == "In terminal"
    assert u1["large_image"] == "terminal"
    assert u1["large_text"] == "Windows Terminal"
    assert u1["state"] == ".venv\\Scripts\\pythonw.exe"

    # 2. Switch foreground to Visual Studio Code
    mock_win32_env["process_instance"].name.return_value = "Code.exe"
    mock_win32_env["gui"].GetWindowText.return_value = "test.py - Visual Studio Code"

    engine.update_once()
    assert len(rpc.updates) == 2
    u2 = rpc.updates[1]
    assert u2["large_image"] == "vscode"
    assert u2["large_text"] == "Visual Studio Code"
    assert u2["details"] == "Editing code"
    assert u2["state"] == "test.py - Visual Studio Code"

    # 3. Switch back to Windows Terminal
    mock_win32_env["process_instance"].name.return_value = "WindowsTerminal.exe"
    mock_win32_env["gui"].GetWindowText.return_value = "PowerShell 7"

    engine.update_once()
    assert len(rpc.updates) == 3
    u3 = rpc.updates[2]
    assert u3["details"] == "In terminal"
    assert u3["large_image"] == "terminal"
    assert u3["large_text"] == "Windows Terminal"
    assert u3["state"] == "PowerShell 7"

