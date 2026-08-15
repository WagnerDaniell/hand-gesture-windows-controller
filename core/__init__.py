"""
Core utilities for filtering, smoothing, and state management.
"""

from .smoothing import OneEuroFilter, ExponentialMovingAverage, CursorSmoother
from .state_machine import GestureStateMachine, GestureState

__all__ = [
    "OneEuroFilter",
    "ExponentialMovingAverage",
    "CursorSmoother",
    "GestureStateMachine",
    "GestureState",
]
