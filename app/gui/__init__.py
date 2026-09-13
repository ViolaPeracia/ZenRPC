"""ZenRPC Desktop GUI Dashboard package."""

from app.gui.controller import GUIController, format_elapsed_time
from app.gui.platform import (
    BasePlatformAdapter,
    WindowsPlatformAdapter,
    LinuxPlatformAdapter,
    get_platform_adapter,
)

__all__ = [
    "GUIController",
    "format_elapsed_time",
    "BasePlatformAdapter",
    "WindowsPlatformAdapter",
    "LinuxPlatformAdapter",
    "get_platform_adapter",
]
