"""
Windows multi-monitor and window management modules.
"""

from .monitor_manager import MonitorManager, MonitorInfo, VirtualDesktopBounds
from .window_controller import WindowController

__all__ = [
    "MonitorManager",
    "MonitorInfo",
    "VirtualDesktopBounds",
    "WindowController",
]
