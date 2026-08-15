"""
Multi-Monitor Detection and Coordinate Mapping for Windows 11.
Supports arbitrary multi-monitor layouts, negative virtual offsets, and seamless desktop spanning.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import screeninfo
import win32api
import win32con


@dataclass
class MonitorInfo:
    """Individual monitor specification."""
    index: int
    name: str
    x: int
    y: int
    width: int
    height: int
    is_primary: bool


@dataclass
class VirtualDesktopBounds:
    """Bounding box covering the entire multi-monitor desktop space."""
    left: int
    top: int
    width: int
    height: int
    right: int
    bottom: int


class MonitorManager:
    """
    Manages display layout queries and maps normalized webcam coordinates to virtual desktop space.
    """

    def __init__(self, mode: str = "span_all", selected_index: int = 0):
        self.mode = mode
        self.selected_index = selected_index
        self.monitors: List[MonitorInfo] = []
        self.virtual_bounds = VirtualDesktopBounds(0, 0, 1920, 1080, 1920, 1080)
        self.refresh_monitors()

    def refresh_monitors(self):
        """Query system monitors via screeninfo and Win32 metrics."""
        self.monitors.clear()
        
        try:
            detected = screeninfo.get_monitors()
            for idx, m in enumerate(detected):
                self.monitors.append(
                    MonitorInfo(
                        index=idx,
                        name=m.name or f"Display {idx + 1}",
                        x=m.x,
                        y=m.y,
                        width=m.width,
                        height=m.height,
                        is_primary=bool(m.is_primary),
                    )
                )
        except Exception:
            # Fallback using win32 primary screen metrics
            w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            self.monitors.append(
                MonitorInfo(
                    index=0,
                    name="Primary Display",
                    x=0,
                    y=0,
                    width=w,
                    height=h,
                    is_primary=True,
                )
            )

        # Query Win32 Virtual Desktop Metrics (accurate for multi-monitors with arbitrary offsets)
        v_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        v_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        v_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        v_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)

        self.virtual_bounds = VirtualDesktopBounds(
            left=v_left,
            top=v_top,
            width=v_width,
            height=v_height,
            right=v_left + v_width,
            bottom=v_top + v_height,
        )

    def map_normalized_to_screen(
        self,
        norm_x: float,
        norm_y: float,
    ) -> Tuple[int, int]:
        """
        Convert normalized ROI coordinates [0.0, 1.0] into Windows virtual desktop pixel coordinates.
        Clamps to valid monitor bounds.
        """
        # Clamp inputs to [0.0, 1.0]
        clamped_x = max(0.0, min(1.0, norm_x))
        clamped_y = max(0.0, min(1.0, norm_y))

        if self.mode == "span_all" or not self.monitors:
            # Span across all connected displays
            screen_x = self.virtual_bounds.left + clamped_x * self.virtual_bounds.width
            screen_y = self.virtual_bounds.top + clamped_y * self.virtual_bounds.height
        else:
            # Lock to selected monitor or primary monitor
            target_monitor = self.get_target_monitor()
            screen_x = target_monitor.x + clamped_x * target_monitor.width
            screen_y = target_monitor.y + clamped_y * target_monitor.height

        # Clamp output to virtual bounds
        final_x = int(round(max(self.virtual_bounds.left, min(self.virtual_bounds.right - 1, screen_x))))
        final_y = int(round(max(self.virtual_bounds.top, min(self.virtual_bounds.bottom - 1, screen_y))))

        return final_x, final_y

    def get_target_monitor(self) -> MonitorInfo:
        """Get the currently active target monitor."""
        if self.mode == "primary_only":
            for m in self.monitors:
                if m.is_primary:
                    return m
            return self.monitors[0] if self.monitors else MonitorInfo(0, "Default", 0, 0, 1920, 1080, True)

        # Selected index
        if 0 <= self.selected_index < len(self.monitors):
            return self.monitors[self.selected_index]

        return self.monitors[0] if self.monitors else MonitorInfo(0, "Default", 0, 0, 1920, 1080, True)

    def get_monitor_at_point(self, x: int, y: int) -> Optional[MonitorInfo]:
        """Find which physical monitor contains the point (x, y)."""
        for m in self.monitors:
            if m.x <= x < (m.x + m.width) and m.y <= y < (m.y + m.height):
                return m
        return None

    def cycle_mode(self) -> str:
        """Cycle between mapping modes: span_all -> primary_only -> selected_monitor."""
        modes = ["span_all", "primary_only"]
        if len(self.monitors) > 1:
            modes.append("selected_monitor")

        curr_idx = modes.index(self.mode) if self.mode in modes else 0
        self.mode = modes[(curr_idx + 1) % len(modes)]
        return self.mode

    def get_summary_text(self) -> str:
        """User-friendly summary of display setup."""
        count = len(self.monitors)
        return (
            f"Monitors: {count} | Mode: {self.mode.upper()} | "
            f"Virtual Desktop: {self.virtual_bounds.width}x{self.virtual_bounds.height}"
        )
