"""
Central Configuration for Hand Gesture Windows Controller.
Contains all tunable hyperparameters, keybindings, display settings, and safety options.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class CameraConfig:
    """Webcam capture and stream settings."""
    camera_id: int = 0
    frame_width: int = 640
    frame_height: int = 480
    target_fps: int = 30
    flip_horizontal: bool = True  # Mirror camera feed for intuitive control


@dataclass
class HandTrackingConfig:
    """MediaPipe Hands detector parameters."""
    max_num_hands: int = 2
    min_detection_confidence: float = 0.70
    min_tracking_confidence: float = 0.70
    model_complexity: int = 1  # 0: Lite, 1: Full


@dataclass
class CalibrationConfig:
    """Active region of interest (ROI) box in the camera frame and cursor speed settings."""
    # Normalized margin percentages inside the camera frame (safe buffer to prevent hand cutoff)
    margin_x_min: float = 0.18
    margin_x_max: float = 0.82
    margin_y_min: float = 0.18
    margin_y_max: float = 0.78
    
    # Cursor speed / sensitivity multiplier (Higher value = faster mouse, less arm movement needed to reach corners)
    speed_multiplier: float = 1.35


@dataclass
class SmoothingConfig:
    """OneEuroFilter and smoothing settings for cursor stabilization."""
    filter_type: str = "one_euro"  # "one_euro" or "ema"
    # OneEuroFilter parameters:
    min_cutoff: float = 0.05  # Ultra-low cutoff at standstill = eliminates hand tremors
    beta: float = 0.08        # High speed responsiveness = zero lag on quick motion
    d_cutoff: float = 1.0     # Derivative cutoff frequency
    # Exponential Moving Average fallback alpha:
    ema_alpha: float = 0.30
    # Deadzone & Deceleration easing:
    deadzone_pixels: float = 2.0   # Absolute freeze radius on full stop
    damping_radius: float = 14.0    # Smoothstep deceleration radius when coming to a halt


@dataclass
class GestureConfig:
    """Gesture classification thresholds and debounce parameters."""
    # Distance between thumb tip (4) and index tip (8) normalized by palm length (0 to 9)
    # When distance < pinch_threshold, it is a pinch (click/drag)
    pinch_threshold: float = 0.32
    pinch_release_threshold: float = 0.45  # Hysteresis to avoid rapid toggling

    # Cooldown and debounce (in frames or seconds)
    click_debounce_frames: int = 2
    state_hold_frames: int = 2

    # Enable drag mode on continuous pinch
    drag_activation_delay_ms: int = 120


@dataclass
class MultiMonitorConfig:
    """Multi-monitor mapping mode."""
    # "span_all": spans all monitors as a single virtual desktop
    # "primary_only": locks control to primary monitor
    # "selected_monitor": locks to a specific monitor index
    mode: str = "span_all"
    selected_monitor_index: int = 0


@dataclass
class UIConfig:
    """Visual style for OpenCV debug HUD window."""
    window_name: str = "Gesture Control HUD - Windows 11"
    show_hud: bool = True
    show_fps: bool = True
    show_landmarks: bool = True
    show_active_zone: bool = True
    show_monitor_preview: bool = True
    
    # Modern HUD Colors (BGR format for OpenCV)
    color_primary: Tuple[int, int, int] = (255, 165, 0)      # Cyan / Light Blue
    color_active_zone: Tuple[int, int, int] = (255, 200, 50) # Light blue ROI box
    color_pointing: Tuple[int, int, int] = (50, 220, 50)     # Neon Green
    color_pinch: Tuple[int, int, int] = (0, 140, 255)        # Vivid Orange
    color_open_hand: Tuple[int, int, int] = (230, 230, 70)   # Sky Blue
    color_fist: Tuple[int, int, int] = (80, 80, 220)         # Soft Red
    color_bg_dark: Tuple[int, int, int] = (25, 25, 30)       # Dark charcoal card background
    color_text: Tuple[int, int, int] = (245, 245, 245)       # Crisp White


@dataclass
class HotkeyConfig:
    """Global emergency hotkeys and control shortcuts."""
    emergency_kill_key: str = "esc"         # Instant stop
    pause_toggle_key: str = "f8"            # Pause / Resume gesture control
    toggle_hud_key: str = "d"               # Toggle HUD details in cv2 window
    switch_monitor_mode_key: str = "m"     # Switch monitor span mode


@dataclass
class AppConfig:
    """Master application configuration container."""
    camera: CameraConfig = field(default_factory=CameraConfig)
    hand: HandTrackingConfig = field(default_factory=HandTrackingConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    monitors: MultiMonitorConfig = field(default_factory=MultiMonitorConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)


# Global default configuration instance
DEFAULT_CONFIG = AppConfig()
