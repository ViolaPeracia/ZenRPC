import sys
import unittest.mock as mock
import pytest

from app.gui.platform import (
    BasePlatformAdapter,
    WindowsPlatformAdapter,
    LinuxPlatformAdapter,
    get_platform_adapter,
)


class DummyWindow:
    def __init__(self, hwnd=12345):
        self._hwnd = hwnd
        self.deiconified = False
        self.state_val = None
        self.lifted = False
        self.focused = False
        self.withdrawn = False

    def winfo_id(self):
        return self._hwnd

    def deiconify(self):
        self.deiconified = True

    def state(self, s=None):
        if s is not None:
            self.state_val = s
        return self.state_val

    def lift(self):
        self.lifted = True

    def focus_force(self):
        self.focused = True

    def withdraw(self):
        self.withdrawn = True


class DummyTrayIcon:
    def __init__(self, title="ZenRPC"):
        self.title = title


def test_get_platform_adapter():
    adapter = get_platform_adapter()
    if sys.platform == "win32":
        assert isinstance(adapter, WindowsPlatformAdapter)
    else:
        assert isinstance(adapter, LinuxPlatformAdapter)


def test_base_platform_adapter_defaults():
    adapter = BasePlatformAdapter()
    win = DummyWindow()

    adapter.restore_and_focus(win)
    assert win.deiconified is True
    assert win.state_val == "normal"
    assert win.lifted is True
    assert win.focused is True

    adapter.minimize_to_tray(win)
    assert win.withdrawn is True

    assert adapter.get_window_hwnd(win) is None
    adapter.hide_console()  # Should not raise


def test_base_platform_adapter_tray_update():
    adapter = BasePlatformAdapter()
    tray = DummyTrayIcon(title="Initial")

    adapter.update_tray_state(tray, locked=True, running=True)
    assert tray.title == "ZenRPC [LOCKED]"

    adapter.update_tray_state(tray, locked=False, running=True)
    assert tray.title == "ZenRPC"

    adapter.update_tray_state(tray, locked=False, running=False)
    assert tray.title == "ZenRPC (RPC Disabled)"

    # Graceful handling of None
    adapter.update_tray_state(None)


def test_linux_platform_adapter_behavior():
    adapter = LinuxPlatformAdapter()
    win = DummyWindow()

    adapter.restore_and_focus(win)
    assert win.deiconified is True
    assert win.state_val == "normal"
    assert win.lifted is True
    assert win.focused is True

    adapter.minimize_to_tray(win)
    assert win.withdrawn is True

    with mock.patch("subprocess.Popen") as mock_popen:
        adapter.open_file_externally("/tmp/test.json")
        mock_popen.assert_called_once_with(["xdg-open", "/tmp/test.json"])


def test_windows_platform_adapter_get_hwnd_success():
    adapter = WindowsPlatformAdapter()
    win = DummyWindow(hwnd=54321)

    with mock.patch("win32gui.GetAncestor", return_value=99999), \
         mock.patch("win32gui.IsWindow", return_value=True):
        hwnd = adapter.get_window_hwnd(win)
        assert hwnd == 99999


def test_windows_platform_adapter_get_hwnd_fallback_ctypes():
    adapter = WindowsPlatformAdapter()
    win = DummyWindow(hwnd=54321)

    # Simulate win32gui missing or returning invalid, fall back to ctypes
    with mock.patch.dict("sys.modules", {"win32gui": None}):
        with mock.patch("ctypes.windll.user32.IsWindow", return_value=True), \
             mock.patch("ctypes.windll.user32.GetParent", return_value=88888):
            hwnd = adapter.get_window_hwnd(win)
            assert hwnd == 88888


def test_windows_platform_adapter_get_hwnd_none():
    adapter = WindowsPlatformAdapter()
    win = DummyWindow(hwnd=0)
    assert adapter.get_window_hwnd(win) is None
    assert adapter.get_window_hwnd(None) is None


def test_windows_platform_adapter_restore_and_focus():
    adapter = WindowsPlatformAdapter()
    win = DummyWindow(hwnd=54321)

    with mock.patch.object(adapter, "get_window_hwnd", return_value=99999), \
         mock.patch.object(adapter, "_win32_force_foreground") as mock_force:
        adapter.restore_and_focus(win)

        assert win.deiconified is True
        assert win.state_val == "normal"
        assert win.lifted is True
        assert win.focused is True
        mock_force.assert_called_once_with(99999)


def test_windows_force_foreground_normal():
    adapter = WindowsPlatformAdapter()

    user32 = mock.MagicMock()
    kernel32 = mock.MagicMock()

    user32.IsWindow.return_value = True
    user32.IsIconic.return_value = False  # Not minimized
    kernel32.GetCurrentThreadId.return_value = 100
    user32.GetForegroundWindow.return_value = 500
    user32.GetWindowThreadProcessId.return_value = 200  # Different thread
    user32.AttachThreadInput.return_value = True

    with mock.patch("ctypes.windll.user32", user32), \
         mock.patch("ctypes.windll.kernel32", kernel32):
        adapter._win32_force_foreground(99999)

        # Restores with SW_SHOW (5) since not iconic
        user32.ShowWindow.assert_called_once_with(99999, 5)
        # Attaches thread input
        user32.AttachThreadInput.assert_any_call(100, 200, True)
        user32.BringWindowToTop.assert_called_once_with(99999)
        user32.SetForegroundWindow.assert_called_once_with(99999)
        # Detaches in finally
        user32.AttachThreadInput.assert_any_call(100, 200, False)


def test_windows_force_foreground_iconic():
    adapter = WindowsPlatformAdapter()

    user32 = mock.MagicMock()
    kernel32 = mock.MagicMock()

    user32.IsWindow.return_value = True
    user32.IsIconic.return_value = True  # Minimized
    kernel32.GetCurrentThreadId.return_value = 100
    user32.GetForegroundWindow.return_value = 0  # No fg window

    with mock.patch("ctypes.windll.user32", user32), \
         mock.patch("ctypes.windll.kernel32", kernel32):
        adapter._win32_force_foreground(99999)

        # Restores with SW_RESTORE (9) since iconic
        user32.ShowWindow.assert_called_once_with(99999, 9)
        user32.BringWindowToTop.assert_called_once_with(99999)
        user32.SetForegroundWindow.assert_called_once_with(99999)
        user32.AttachThreadInput.assert_not_called()


def test_windows_force_foreground_always_detaches_on_exception():
    adapter = WindowsPlatformAdapter()

    user32 = mock.MagicMock()
    kernel32 = mock.MagicMock()

    user32.IsWindow.return_value = True
    user32.IsIconic.return_value = False
    kernel32.GetCurrentThreadId.return_value = 100
    user32.GetForegroundWindow.return_value = 500
    user32.GetWindowThreadProcessId.return_value = 200
    user32.AttachThreadInput.return_value = True
    user32.SetForegroundWindow.side_effect = RuntimeError("OS Lock")

    with mock.patch("ctypes.windll.user32", user32), \
         mock.patch("ctypes.windll.kernel32", kernel32):
        # Should not raise
        adapter._win32_force_foreground(99999)

        # Must detach in finally despite error in SetForegroundWindow
        user32.AttachThreadInput.assert_any_call(100, 200, False)


def test_windows_platform_adapter_minimize_to_tray():
    adapter = WindowsPlatformAdapter()
    win = DummyWindow()

    adapter.minimize_to_tray(win)
    assert win.withdrawn is True


def test_windows_platform_adapter_open_file():
    adapter = WindowsPlatformAdapter()
    with mock.patch("os.startfile") as mock_startfile:
        adapter.open_file_externally("C:\\test\\config.json")
        mock_startfile.assert_called_once_with("C:\\test\\config.json")


def test_windows_hide_console_shared_terminal():
    """Does NOT hide console when running in an interactive shared terminal (count > 1)."""
    adapter = WindowsPlatformAdapter()
    kernel32 = mock.MagicMock()
    user32 = mock.MagicMock()

    kernel32.GetConsoleWindow.return_value = 1234
    kernel32.GetConsoleProcessList.return_value = 2  # Shared with shell

    with mock.patch("ctypes.windll.kernel32", kernel32), \
         mock.patch("ctypes.windll.user32", user32):
        adapter.hide_console()
        user32.ShowWindow.assert_not_called()


def test_windows_hide_console_exclusive_process():
    """Hides console when running exclusively owned console (count == 1)."""
    adapter = WindowsPlatformAdapter()
    kernel32 = mock.MagicMock()
    user32 = mock.MagicMock()

    kernel32.GetConsoleWindow.return_value = 1234
    kernel32.GetConsoleProcessList.return_value = 1  # Exclusively owned

    with mock.patch("ctypes.windll.kernel32", kernel32), \
         mock.patch("ctypes.windll.user32", user32):
        adapter.hide_console()
        user32.ShowWindow.assert_called_once_with(1234, 0)


def test_dashboard_delegates_to_platform_adapter():
    """ZenRPCDashboard cleanly delegates restore, minimize, and tray updates to platform adapter."""
    from app.gui.dashboard import ZenRPCDashboard
    from app.gui.controller import GUIController
    from app.presence import PresenceEngine

    mock_adapter = mock.MagicMock(spec=BasePlatformAdapter)
    engine = PresenceEngine()
    controller = GUIController(engine=engine)
    tray = DummyTrayIcon()

    dashboard = ZenRPCDashboard(
        controller=controller,
        tray_icon=tray,
        platform_adapter=mock_adapter,
    )
    try:
        # Test minimize_to_tray
        dashboard.minimize_to_tray()
        mock_adapter.minimize_to_tray.assert_called_with(dashboard)

        # Test restore_window
        dashboard.restore_window()
        mock_adapter.restore_and_focus.assert_called_with(dashboard)

        # Test on_closing with minimize_to_tray enabled in config
        with mock.patch.object(controller, "get_config", return_value={"minimize_to_tray": True}):
            mock_adapter.reset_mock()
            dashboard.on_closing()
            mock_adapter.minimize_to_tray.assert_called_with(dashboard)

        # Test _on_controller_update delegates to update_tray_state
        mock_adapter.reset_mock()
        dashboard._on_controller_update({
            "running": True,
            "connected": True,
            "locked": True,
            "locked_proc": "Code.exe",
            "proc_name": "Code.exe",
            "app_name": "VS Code",
            "detail": "Editing",
            "state_text": "main.py",
            "icon_key": "vscode",
            "elapsed_seconds": 45,
        })
        mock_adapter.update_tray_state.assert_called_with(tray, locked=True, running=True)
    finally:
        dashboard.quit_app()

