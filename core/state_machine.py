"""
Gesture State Machine with Debounce, Hysteresis, and Cooldown.
Prevents accidental multi-clicks, state flickering, and manages mouse action lifecycle.
"""

from enum import Enum, auto
import time
from typing import Optional, Dict, Any


class GestureState(Enum):
    """Recognized discrete gesture states."""
    UNKNOWN = auto()
    POINTING = auto()       # Index finger raised -> Cursor control (Neutral)
    CLICK = auto()          # Two fingers (✌️) or Quick Pinch (👌) -> Dedicated Single Left Click
    PINCH_DRAG = auto()     # Legacy compatibility
    OPEN_HAND = auto()      # All fingers extended (🖐️) -> Left Click Down / Drag Window
    FIST = auto()           # Closed fist (✊) -> Safety lock / Neutral pause


class GestureStateMachine:
    """
    Manages gesture state transitions with debounce confirmation and cooldown timers.
    """

    def __init__(
        self,
        debounce_frames: int = 2,
        cooldown_seconds: float = 0.05,
    ):
        self.debounce_frames = debounce_frames
        self.cooldown_seconds = cooldown_seconds

        self.current_state: GestureState = GestureState.UNKNOWN
        self.candidate_state: GestureState = GestureState.UNKNOWN
        self.candidate_frame_count: int = 0

        self.last_state_change_time: float = 0.0
        self.is_mouse_down: bool = False
        self.is_paused: bool = False
        self.drag_start_time: Optional[float] = None

    def update(self, raw_gesture: GestureState) -> Dict[str, Any]:
        """
        Process a new raw gesture classification from the current video frame.
        Returns a dictionary of action flags:
        {
            'state': GestureState,
            'state_changed': bool,
            'action': str, # 'mouse_move', 'click', 'mouse_down', 'mouse_drag', 'mouse_up', 'pause', 'idle'
            'is_mouse_down': bool,
            'is_paused': bool
        }
        """
        now = time.perf_counter()
        state_changed = False
        action = "idle"

        # If globally paused, force FIST/PAUSED behavior
        if self.is_paused:
            if self.is_mouse_down:
                self.is_mouse_down = False
                action = "mouse_up"
            return {
                "state": GestureState.FIST,
                "state_changed": False,
                "action": action,
                "is_mouse_down": self.is_mouse_down,
                "is_paused": True,
            }

        # Debounce logic: Candidate state must match for N consecutive frames
        if raw_gesture == self.candidate_state:
            self.candidate_frame_count += 1
        else:
            self.candidate_state = raw_gesture
            self.candidate_frame_count = 1

        # Check if candidate is confirmed and cooldown has passed
        if (
            self.candidate_frame_count >= self.debounce_frames
            and self.candidate_state != self.current_state
            and (now - self.last_state_change_time) >= self.cooldown_seconds
        ):
            prev_state = self.current_state
            self.current_state = self.candidate_state
            self.last_state_change_time = now
            state_changed = True

            # Process state transitions
            if self.current_state == GestureState.OPEN_HAND:
                # Open hand activates hold / drag
                if not self.is_mouse_down:
                    self.is_mouse_down = True
                    self.drag_start_time = now
                    action = "mouse_down"
                else:
                    action = "mouse_drag"

            elif self.current_state in (GestureState.CLICK, GestureState.PINCH_DRAG):
                # Dedicated single click
                if self.is_mouse_down:
                    self.is_mouse_down = False
                    self.drag_start_time = None
                    action = "mouse_up"
                else:
                    action = "click"

            elif self.current_state in (GestureState.POINTING, GestureState.UNKNOWN):
                if self.is_mouse_down:
                    self.is_mouse_down = False
                    self.drag_start_time = None
                    action = "mouse_up"
                else:
                    action = "mouse_move"

            elif self.current_state == GestureState.FIST:
                if self.is_mouse_down:
                    self.is_mouse_down = False
                    self.drag_start_time = None
                    action = "mouse_up"
                else:
                    action = "pause"

        else:
            # Steady state actions
            if self.current_state == GestureState.OPEN_HAND:
                action = "mouse_drag" if self.is_mouse_down else "mouse_down"
            elif self.current_state in (GestureState.CLICK, GestureState.PINCH_DRAG, GestureState.POINTING, GestureState.UNKNOWN):
                action = "mouse_move"
            elif self.current_state == GestureState.FIST:
                action = "pause"
            else:
                action = "idle"

        return {
            "state": self.current_state,
            "state_changed": state_changed,
            "action": action,
            "is_mouse_down": self.is_mouse_down,
            "is_paused": self.is_paused,
        }

    def toggle_pause(self) -> bool:
        """Toggle global pause state."""
        self.is_paused = not self.is_paused
        if self.is_paused and self.is_mouse_down:
            self.is_mouse_down = False
        return self.is_paused

    def set_pause(self, paused: bool):
        """Set pause state directly."""
        self.is_paused = paused
        if self.is_paused and self.is_mouse_down:
            self.is_mouse_down = False

    def reset(self):
        """Reset state machine."""
        self.current_state = GestureState.UNKNOWN
        self.candidate_state = GestureState.UNKNOWN
        self.candidate_frame_count = 0
        self.is_mouse_down = False
        self.drag_start_time = None
