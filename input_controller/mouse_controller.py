"""
High-Performance Windows Mouse Emulation.
Uses direct Win32 ctypes APIs for ultra-low latency cursor movement and drag operations.
"""

import ctypes
from typing import Optional, Tuple
import pyautogui

# Set PyAutoGUI flags for responsiveness
pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = False

# Win32 Mouse Event Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


class MouseController:
    """
    Simulates mouse movements, clicks, and window dragging with zero input lag.
    """

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.is_left_down: bool = False
        self.is_right_down: bool = False
        self.last_x: int = 0
        self.last_y: int = 0

    def move_to(self, x: int, y: int):
        """Move cursor directly to target screen coordinates (supports multi-monitors)."""
        self.user32.SetCursorPos(int(x), int(y))
        self.last_x = int(x)
        self.last_y = int(y)

    def mouse_down(self, x: Optional[int] = None, y: Optional[int] = None):
        """Press and hold left mouse button (initiates drag)."""
        if x is not None and y is not None:
            self.move_to(x, y)

        if not self.is_left_down:
            self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self.is_left_down = True

    def mouse_up(self, x: Optional[int] = None, y: Optional[int] = None):
        """Release left mouse button (ends drag / drops window)."""
        if x is not None and y is not None:
            self.move_to(x, y)

        if self.is_left_down:
            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.is_left_down = False

    def click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Perform a single left click."""
        if x is not None and y is not None:
            self.move_to(x, y)
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.is_left_down = False

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Perform a single right click."""
        if x is not None and y is not None:
            self.move_to(x, y)
        self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def get_position(self) -> Tuple[int, int]:
        """Get current cursor position from Windows."""
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        self.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def release_all(self):
        """Safety release of all pressed buttons."""
        if self.is_left_down:
            self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.is_left_down = False
        if self.is_right_down:
            self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            self.is_right_down = False
