"""
Windows Window Controller using native Win32 APIs.
Inspects, grabs, moves, snaps, and transfers windows across monitors.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import win32api
import win32con
import win32gui
from window_manager.monitor_manager import MonitorInfo, MonitorManager


@dataclass
class WindowInfo:
    """Active window metadata."""
    hwnd: int
    title: str
    class_name: str
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    width: int
    height: int
    is_maximized: bool


class WindowController:
    """
    Win32 Window controller providing direct window manipulation and multi-monitor window transfer.
    """

    # Windows system classes to ignore when grabbing windows
    IGNORED_CLASSES = {
        "Progman",
        "WorkerW",
        "Shell_TrayWnd",
        "Shell_SecondaryTrayWnd",
        "Windows.UI.Core.CoreWindow",
    }

    def get_window_under_cursor(self, x: int, y: int) -> Optional[WindowInfo]:
        """
        Locate the top-level application window under (x, y) coordinates.
        """
        try:
            point_hwnd = win32gui.WindowFromPoint((x, y))
            if not point_hwnd:
                return None

            # Retrieve top-level root window ancestor
            root_hwnd = win32gui.GetAncestor(point_hwnd, win32con.GA_ROOT)
            if not root_hwnd:
                root_hwnd = point_hwnd

            if not win32gui.IsWindow(root_hwnd) or not win32gui.IsWindowVisible(root_hwnd):
                return None

            class_name = win32gui.GetClassName(root_hwnd)
            if class_name in self.IGNORED_CLASSES:
                return None

            title = win32gui.GetWindowText(root_hwnd)
            rect = win32gui.GetWindowRect(root_hwnd)  # (left, top, right, bottom)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            # Check if maximized
            placement = win32gui.GetWindowPlacement(root_hwnd)
            is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED

            return WindowInfo(
                hwnd=root_hwnd,
                title=title or f"Window 0x{root_hwnd:X}",
                class_name=class_name,
                rect=rect,
                width=width,
                height=height,
                is_maximized=is_maximized,
            )
        except Exception:
            return None

    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Retrieve the currently focused foreground window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or not win32gui.IsWindow(hwnd):
                return None

            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            placement = win32gui.GetWindowPlacement(hwnd)
            is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                rect=rect,
                width=width,
                height=height,
                is_maximized=is_maximized,
            )
        except Exception:
            return None

    def move_window_relative(self, hwnd: int, delta_x: int, delta_y: int):
        """Move a window by a relative delta offset."""
        try:
            if not win32gui.IsWindow(hwnd):
                return

            rect = win32gui.GetWindowRect(hwnd)
            new_x = rect[0] + delta_x
            new_y = rect[1] + delta_y
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            win32gui.SetWindowPos(
                hwnd,
                None,
                new_x,
                new_y,
                width,
                height,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
        except Exception:
            pass

    def move_window_to_point(self, hwnd: int, x: int, y: int):
        """Set top-left position of window directly."""
        try:
            if not win32gui.IsWindow(hwnd):
                return

            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            win32gui.SetWindowPos(
                hwnd,
                None,
                x,
                y,
                width,
                height,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
        except Exception:
            pass

    def snap_to_monitor(
        self,
        hwnd: int,
        monitor: MonitorInfo,
        position: str = "maximize",
    ):
        """
        Snap window to a specific monitor partition:
        position: 'maximize', 'left_half', 'right_half', 'center'
        """
        try:
            if not win32gui.IsWindow(hwnd):
                return

            # If maximized and snapping to half, restore first
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            if position == "maximize":
                # Move into monitor area first, then maximize
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    monitor.x + 50,
                    monitor.y + 50,
                    monitor.width - 100,
                    monitor.height - 100,
                    win32con.SWP_NOZORDER,
                )
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

            elif position == "left_half":
                half_w = monitor.width // 2
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    monitor.x,
                    monitor.y,
                    half_w,
                    monitor.height,
                    win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
                )

            elif position == "right_half":
                half_w = monitor.width // 2
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    monitor.x + half_w,
                    monitor.y,
                    half_w,
                    monitor.height,
                    win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
                )

            elif position == "center":
                w = int(monitor.width * 0.7)
                h = int(monitor.height * 0.7)
                x = monitor.x + (monitor.width - w) // 2
                y = monitor.y + (monitor.height - h) // 2
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    x,
                    y,
                    w,
                    h,
                    win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
                )
        except Exception:
            pass

    def send_window_to_next_monitor(self, hwnd: int, monitor_mgr: MonitorManager):
        """Transfer window to the adjacent monitor, scaling position proportionately."""
        try:
            if len(monitor_mgr.monitors) < 2 or not win32gui.IsWindow(hwnd):
                return

            rect = win32gui.GetWindowRect(hwnd)
            center_x = (rect[0] + rect[2]) // 2
            center_y = (rect[1] + rect[3]) // 2

            current_mon = monitor_mgr.get_monitor_at_point(center_x, center_y)
            if not current_mon:
                current_mon = monitor_mgr.monitors[0]

            curr_idx = current_mon.index
            next_idx = (curr_idx + 1) % len(monitor_mgr.monitors)
            next_mon = monitor_mgr.monitors[next_idx]

            # Calculate relative offset inside current monitor
            rel_x = (rect[0] - current_mon.x) / max(1, current_mon.width)
            rel_y = (rect[1] - current_mon.y) / max(1, current_mon.height)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            new_x = int(next_mon.x + rel_x * next_mon.width)
            new_y = int(next_mon.y + rel_y * next_mon.height)

            win32gui.SetWindowPos(
                hwnd,
                None,
                new_x,
                new_y,
                min(width, next_mon.width),
                min(height, next_mon.height),
                win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW,
            )
        except Exception:
            pass
