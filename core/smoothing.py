"""
Cursor Smoothing and Jitter Reduction Filters.
Implements the 1€ (One Euro) Filter and Exponential Moving Average (EMA)
specifically optimized for hand landmark tracking on Windows 11.
"""

import math
import time
from typing import Optional, Tuple


class LowPassFilter:
    """Standard first-order low-pass filter."""

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.s: Optional[float] = None

    def filter(self, value: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if self.s is None:
            self.s = value
        else:
            self.s = self.alpha * value + (1.0 - self.alpha) * self.s
        return self.s

    def reset(self):
        self.s = None


class OneEuroFilter:
    """
    1€ Filter: A fast, adaptive low-pass filter for noisy human input.
    - Suppresses jitter at low speeds (very smooth precision).
    - Minimizes lag/latency at high speeds (instant flick response).
    
    Reference: Géry Casiez, Nicolas Roussel, Daniel Vogel. 
    1 € Filter: A Simple Speed-based Low-pass Filter for Noisy Input in HCI. 
    CHI '12, May 2012, Austin, TX, USA.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        
        self.x_filter = LowPassFilter()
        self.dx_filter = LowPassFilter()
        self.last_time: Optional[float] = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, value: float, timestamp: Optional[float] = None) -> float:
        if timestamp is None:
            timestamp = time.perf_counter()

        if self.last_time is None:
            self.last_time = timestamp
            self.dx_filter.filter(0.0)
            return self.x_filter.filter(value)

        dt = timestamp - self.last_time
        if dt <= 0.0:
            dt = 1e-5  # Prevent division by zero

        self.last_time = timestamp

        # Estimate the derivative (speed of movement)
        prev_x = self.x_filter.s if self.x_filter.s is not None else value
        dx = (value - prev_x) / dt
        edx = self.dx_filter.filter(dx, self._alpha(self.d_cutoff, dt))

        # Dynamically adjust cutoff frequency based on speed
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filter.filter(value, self._alpha(cutoff, dt))

    def reset(self):
        self.x_filter.reset()
        self.dx_filter.reset()
        self.last_time = None


class ExponentialMovingAverage:
    """Simple Exponential Moving Average filter for 2D coordinates."""

    def __init__(self, alpha: float = 0.35):
        self.alpha = alpha
        self.prev_x: Optional[float] = None
        self.prev_y: Optional[float] = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self.prev_x is None or self.prev_y is None:
            self.prev_x = x
            self.prev_y = y
            return x, y

        smoothed_x = self.alpha * x + (1.0 - self.alpha) * self.prev_x
        smoothed_y = self.alpha * y + (1.0 - self.alpha) * self.prev_y
        self.prev_x = smoothed_x
        self.prev_y = smoothed_y
        return smoothed_x, smoothed_y

    def reset(self):
        self.prev_x = None
        self.prev_y = None


class CursorSmoother:
    """
    Unified 2D coordinate smoother with deadzone suppression, smoothstep deceleration,
    and adaptive 1€ / EMA filtering to eliminate hand tremors on standstill.
    """

    def __init__(
        self,
        filter_type: str = "one_euro",
        min_cutoff: float = 0.05,
        beta: float = 0.08,
        d_cutoff: float = 1.0,
        ema_alpha: float = 0.30,
        deadzone_pixels: float = 2.0,
        damping_radius: float = 14.0,
    ):
        self.filter_type = filter_type
        self.deadzone_pixels = deadzone_pixels
        self.damping_radius = max(damping_radius, deadzone_pixels + 0.1)
        
        self.one_euro_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
        self.one_euro_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
        self.ema = ExponentialMovingAverage(alpha=ema_alpha)

        self.last_output_x: Optional[float] = None
        self.last_output_y: Optional[float] = None

    def smooth(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[int, int]:
        """Apply filtering and smoothstep deceleration damping to (x, y) target coordinates."""
        if self.filter_type == "one_euro":
            filtered_x = self.one_euro_x.filter(x, timestamp)
            filtered_y = self.one_euro_y.filter(y, timestamp)
        else:
            filtered_x, filtered_y = self.ema.filter(x, y)

        if self.last_output_x is not None and self.last_output_y is not None:
            distance = math.hypot(filtered_x - self.last_output_x, filtered_y - self.last_output_y)
            
            # 1. Full stop deadzone: completely freeze micro-jitter when hand stops
            if distance <= self.deadzone_pixels:
                return int(round(self.last_output_x)), int(round(self.last_output_y))
            
            # 2. Smoothstep deceleration easing: gently transition between moving and stopping
            if distance < self.damping_radius:
                ratio = (distance - self.deadzone_pixels) / (self.damping_radius - self.deadzone_pixels)
                # Hermite interpolation (smoothstep): S(t) = 3t^2 - 2t^3
                ease_factor = ratio * ratio * (3.0 - 2.0 * ratio)
                filtered_x = self.last_output_x + (filtered_x - self.last_output_x) * ease_factor
                filtered_y = self.last_output_y + (filtered_y - self.last_output_y) * ease_factor

        self.last_output_x = filtered_x
        self.last_output_y = filtered_y
        return int(round(filtered_x)), int(round(filtered_y))

    def reset(self):
        """Reset internal filter states when tracking is lost."""
        self.one_euro_x.reset()
        self.one_euro_y.reset()
        self.ema.reset()
        self.last_output_x = None
        self.last_output_y = None
