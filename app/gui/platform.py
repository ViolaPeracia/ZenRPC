import ctypes
import logging
import os
import subprocess
import sys
from typing import Any, Optional

logger = logging.getLogger("zenrpc.platform")


class BasePlatformAdapter:
    """
    Lightweight platform adapter defining window and OS-specific desktop interactions.
    Keeps GUI and business logic decoupled from operating system APIs.
    """

    def restore_and_focus(self, window: Any) -> None:
        """Restores window from minimized or withdrawn state and brings it to the foreground."""
        try:
            window.deiconify()
            window.state("normal")
            window.lift()
            window.focus_force()
        except Exception as e:
            logger.debug("Failed restoring and focusing window: %s", e)

    def minimize_to_tray(self, window: Any) -> None:
        """Minimizes window to system tray by withdrawing it from screen and taskbar."""
        try:
            window.withdraw()
        except Exception as e:
            logger.debug("Failed minimizing window to tray: %s", e)

    def open_file_externally(self, path: str) -> None:
        """Opens a file using the operating system's default handler."""
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            logger.warning("Could not open file %s: %s", path, e)

    def hide_console(self) -> None:
        """Suppresses console window where applicable."""
        pass

    def update_tray_state(
        self,
        tray_icon: Any,
        locked: bool = False,
        running: bool = True,
    ) -> None:
        """Updates tray icon state (e.g. tooltip title) safely without extra dependencies."""
        if not tray_icon:
            return
        try:
            title = "ZenRPC [LOCKED]" if locked else ("ZenRPC" if running else "ZenRPC (RPC Disabled)")
            if hasattr(tray_icon, "title") and tray_icon.title != title:
                tray_icon.title = title
        except Exception as e:
            logger.debug("Failed updating tray state: %s", e)

    def get_window_hwnd(self, window: Any) -> Optional[int]:
        """Returns the native OS window handle (HWND) if supported, else None."""
        return None


class WindowsPlatformAdapter(BasePlatformAdapter):
    """
    Windows-specific platform adapter using Win32 user32/kernel32 APIs for robust
    window restoration, foreground focus bypassing Windows restrictions, and console hiding.
    """

    def get_window_hwnd(self, window: Any) -> Optional[int]:
        """Resolves the top-level Win32 HWND for a Tkinter/CustomTkinter window."""
        try:
            winfo_id = getattr(window, "winfo_id", None)
            if not callable(winfo_id):
                return None
            child_hwnd = winfo_id()
            if not child_hwnd:
                return None

            try:
                import win32gui
                # GA_ROOT = 2
                root_hwnd = win32gui.GetAncestor(child_hwnd, 2)
                if root_hwnd and win32gui.IsWindow(root_hwnd):
                    return root_hwnd
            except Exception:
                pass

            if ctypes.windll.user32.IsWindow(child_hwnd):
                parent = ctypes.windll.user32.GetParent(child_hwnd)
                return parent if parent else child_hwnd
        except Exception as e:
            logger.debug("Error resolving HWND for window: %s", e)
        return None

    def restore_and_focus(self, window: Any) -> None:
        """
        Restores dashboard window from tray and brings it to the foreground on Windows.
        Bypasses Windows foreground lock restrictions using AttachThreadInput and BringWindowToTop.
        """
        try:
            window.deiconify()
            window.state("normal")
        except Exception as e:
            logger.debug("deiconify/state call failed: %s", e)

        hwnd = self.get_window_hwnd(window)
        if hwnd:
            self._win32_force_foreground(hwnd)

        try:
            window.lift()
            window.focus_force()
        except Exception as e:
            logger.debug("lift/focus_force failed: %s", e)

    def _win32_force_foreground(self, hwnd: int) -> None:
        """Safely forces a Win32 window to the foreground, detaching thread input in finally."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            if not user32.IsWindow(hwnd):
                return

            # SW_RESTORE = 9, SW_SHOW = 5
            try:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)
                else:
                    user32.ShowWindow(hwnd, 5)
            except Exception as e:
                logger.debug("ShowWindow failed for HWND %s: %s", hwnd, e)

            attached = False
            current_thread_id = kernel32.GetCurrentThreadId()
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread_id = 0
            if fg_hwnd:
                pid_buf = ctypes.c_ulong()
                fg_thread_id = user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid_buf))

            try:
                if fg_thread_id and fg_thread_id != current_thread_id:
                    try:
                        if user32.AttachThreadInput(current_thread_id, fg_thread_id, True):
                            attached = True
                    except Exception as e:
                        logger.debug("AttachThreadInput failed: %s", e)

                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
            except Exception as e:
                logger.debug("BringWindowToTop / SetForegroundWindow failed: %s", e)
            finally:
                if attached and fg_thread_id:
                    try:
                        user32.AttachThreadInput(current_thread_id, fg_thread_id, False)
                    except Exception as e:
                        logger.debug("AttachThreadInput detach failed: %s", e)
        except Exception as e:
            logger.debug("Win32 force foreground failed: %s", e)

    def open_file_externally(self, path: str) -> None:
        """Opens a file using Windows default file association via os.startfile."""
        try:
            os.startfile(path)
        except Exception as e:
            logger.warning("Could not open file %s: %s", path, e)

    def hide_console(self) -> None:
        """
        Hides the console window only when the console was created exclusively for this process
        (e.g. double-clicked without pythonw). Does NOT hide when intentionally launched from a terminal.
        """
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if not hwnd:
                return

            # Check process count attached to this console
            pids = (ctypes.c_uint * 2)()
            count = ctypes.windll.kernel32.GetConsoleProcessList(pids, 2)
            if count == 1:
                # Exclusively owned console (e.g. launcher/explorer without pythonw)
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception as e:
            logger.debug("Failed checking/hiding Windows console: %s", e)


class LinuxPlatformAdapter(BasePlatformAdapter):
    """
    Linux-specific platform adapter reproducing the frozen Linux GUI behavior from da21ce7.
    """

    def restore_and_focus(self, window: Any) -> None:
        """Restores window from tray and brings to top via standard Tkinter protocols."""
        try:
            window.deiconify()
            window.state("normal")
            window.lift()
            window.focus_force()
        except Exception as e:
            logger.debug("Failed restoring Linux window: %s", e)

    def minimize_to_tray(self, window: Any) -> None:
        """Minimizes window to tray by withdrawing."""
        try:
            window.withdraw()
        except Exception as e:
            logger.debug("Failed withdrawing Linux window: %s", e)

    def open_file_externally(self, path: str) -> None:
        """Opens file with xdg-open on Linux."""
        try:
            subprocess.Popen(["xdg-open", path])
        except Exception as e:
            logger.warning("Could not open file %s: %s", path, e)

    def hide_console(self) -> None:
        """No-op on Linux."""
        pass


def get_platform_adapter() -> BasePlatformAdapter:
    """Factory returning the appropriate platform adapter for the running OS."""
    if sys.platform == "win32":
        return WindowsPlatformAdapter()
    return LinuxPlatformAdapter()
