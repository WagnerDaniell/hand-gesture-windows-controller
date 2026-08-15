"""
Modern HUD and Visual Overlay Renderer for OpenCV Window.
Draws sleek status banners, active zone calibration boxes, gestures, and multi-monitor indicators.
"""

from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from config import CalibrationConfig, UIConfig
from core.state_machine import GestureState
from vision.hand_detector import HandLandmarks
from window_manager.monitor_manager import MonitorManager


class HUDRenderer:
    """
    Renders visual debug elements, status cards, and gestures on the video stream.
    """

    def __init__(
        self,
        ui_config: UIConfig,
        calib_config: CalibrationConfig,
        monitor_mgr: MonitorManager,
    ):
        self.cfg = ui_config
        self.calib = calib_config
        self.mon_mgr = monitor_mgr

    def render(
        self,
        frame: np.ndarray,
        hand: Optional[HandLandmarks],
        current_state: GestureState,
        action: str,
        is_mouse_down: bool,
        is_paused: bool,
        screen_pos: Tuple[int, int],
        smoothed_pos: Tuple[int, int],
        fps: float,
        metrics: Optional[Dict[str, any]] = None,
    ) -> np.ndarray:
        """Draw complete HUD layer on top of video frame."""
        h, w, _ = frame.shape
        overlay = frame.copy()

        # 1. Draw Active ROI Calibration Box
        if self.cfg.show_active_zone:
            self._draw_active_zone(overlay, w, h, current_state)

        # 2. Draw Hand Landmark highlights
        if hand and self.cfg.show_landmarks:
            self._draw_hand_highlights(overlay, hand, current_state, metrics)

        # 3. Draw Top Status Card (Gesture, Mouse State, System State)
        self._draw_status_card(
            overlay,
            current_state,
            action,
            is_mouse_down,
            is_paused,
            hand is not None,
        )

        # 4. Draw Metric & Multi-Monitor Info Panel (Top Right)
        if self.cfg.show_hud:
            self._draw_info_panel(overlay, w, h, screen_pos, fps, metrics)

        # 5. Draw Bottom Navigation & Hotkey Bar
        self._draw_footer_bar(overlay, w, h, is_paused)

        return overlay

    def _draw_active_zone(
        self,
        img: np.ndarray,
        w: int,
        h: int,
        state: GestureState,
    ):
        """Draw calibrated active zone bounding box with corner brackets."""
        x1 = int(self.calib.margin_x_min * w)
        y1 = int(self.calib.margin_y_min * h)
        x2 = int(self.calib.margin_x_max * w)
        y2 = int(self.calib.margin_y_max * h)

        # Subtle semi-transparent border box
        color_box = (180, 140, 40) if state != GestureState.PINCH_DRAG else (0, 165, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color_box, 1, cv2.LINE_AA)

        # Corner bracket accents for aesthetic look
        corner_len = 18
        bracket_color = (255, 220, 100) if state != GestureState.PINCH_DRAG else (0, 200, 255)
        th = 2

        # Top-left
        cv2.line(img, (x1, y1), (x1 + corner_len, y1), bracket_color, th)
        cv2.line(img, (x1, y1), (x1, y1 + corner_len), bracket_color, th)

        # Top-right
        cv2.line(img, (x2, y1), (x2 - corner_len, y1), bracket_color, th)
        cv2.line(img, (x2, y1), (x2, y1 + corner_len), bracket_color, th)

        # Bottom-left
        cv2.line(img, (x1, y2), (x1 + corner_len, y2), bracket_color, th)
        cv2.line(img, (x1, y2), (x1, y2 - corner_len), bracket_color, th)

        # Bottom-right
        cv2.line(img, (x2, y2), (x2 - corner_len, y2), bracket_color, th)
        cv2.line(img, (x2, y2), (x2, y2 - corner_len), bracket_color, th)

        # Label
        cv2.putText(
            img,
            "ACTIVE DESKTOP ZONE",
            (x1 + 6, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )

    def _draw_hand_highlights(
        self,
        img: np.ndarray,
        hand: HandLandmarks,
        state: GestureState,
        metrics: Optional[Dict[str, any]],
    ):
        """Draw interactive visuals on fingertips (e.g. cursor point, pinch line)."""
        lm = hand.landmarks
        index_tip = lm[8]
        thumb_tip = lm[4]

        # Draw line between thumb and index with proximity color
        if metrics and "norm_pinch_dist" in metrics:
            dist = metrics["norm_pinch_dist"]
            # Color interpolates from Blue/Cyan (far) to Orange/Red (pinched)
            t = max(0.0, min(1.0, 1.0 - (dist / 0.5)))
            line_color = (
                int(255 * (1 - t)),
                int(165 * (1 - t) + 200 * t),
                int(255 * t),
            )
            cv2.line(
                img,
                (thumb_tip.px, thumb_tip.py),
                (index_tip.px, index_tip.py),
                line_color,
                2,
                cv2.LINE_AA,
            )

        # Draw glowing halo around index fingertip (primary cursor point)
        pt_color = (0, 230, 0) if state == GestureState.POINTING else (0, 160, 255)
        cv2.circle(img, (index_tip.px, index_tip.py), 8, pt_color, -1, cv2.LINE_AA)
        cv2.circle(img, (index_tip.px, index_tip.py), 14, pt_color, 2, cv2.LINE_AA)

        # Draw thumb tip circle
        cv2.circle(img, (thumb_tip.px, thumb_tip.py), 6, (255, 200, 50), -1, cv2.LINE_AA)

    def _draw_status_card(
        self,
        img: np.ndarray,
        state: GestureState,
        action: str,
        is_mouse_down: bool,
        is_paused: bool,
        has_hand: bool,
    ):
        """Draw modern top-left gesture badge card."""
        card_x, card_y = 12, 12
        card_w, card_h = 240, 72

        # Draw dark translucent card background
        self._draw_rounded_card(img, card_x, card_y, card_w, card_h, (25, 25, 30), alpha=0.85)

        # Determine Badge Style
        if is_paused:
            badge_text = "PAUSED"
            badge_color = (60, 60, 220)
            status_desc = "Press F8 to Resume"
        elif not has_hand:
            badge_text = "LOOKING FOR HAND"
            badge_color = (130, 130, 130)
            status_desc = "Show hand to camera"
        elif state == GestureState.POINTING:
            badge_text = "POINTING"
            badge_color = (50, 210, 50)
            status_desc = "Cursor Control Active"
        elif state == GestureState.PINCH_DRAG:
            badge_text = "PINCH / DRAG"
            badge_color = (0, 140, 255)
            status_desc = "Left Click Down (Dragging)" if is_mouse_down else "Pinch Detected"
        elif state == GestureState.OPEN_HAND:
            badge_text = "OPEN HAND"
            badge_color = (240, 200, 60)
            status_desc = "Released / Hover Mode"
        elif state == GestureState.FIST:
            badge_text = "CLOSED FIST"
            badge_color = (90, 90, 220)
            status_desc = "Safety Pause Lock"
        else:
            badge_text = "NEUTRAL"
            badge_color = (160, 160, 160)
            status_desc = "Ready"

        # Draw colored indicator pill
        cv2.circle(img, (card_x + 18, card_y + 24), 8, badge_color, -1, cv2.LINE_AA)
        cv2.putText(
            img,
            badge_text,
            (card_x + 36, card_y + 30),
            cv2.FONT_HERSHEY_DUPLEX,
            0.62,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # Subtitle description
        cv2.putText(
            img,
            status_desc,
            (card_x + 16, card_y + 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (190, 190, 190),
            1,
            cv2.LINE_AA,
        )

    def _draw_info_panel(
        self,
        img: np.ndarray,
        w: int,
        h: int,
        screen_pos: Tuple[int, int],
        fps: float,
        metrics: Optional[Dict[str, any]],
    ):
        """Draw top-right telemetry dashboard card."""
        panel_w, panel_h = 220, 80
        panel_x = w - panel_w - 12
        panel_y = 12

        self._draw_rounded_card(img, panel_x, panel_y, panel_w, panel_h, (25, 25, 30), alpha=0.85)

        # FPS counter
        fps_color = (80, 220, 80) if fps >= 25 else (50, 140, 240)
        cv2.putText(
            img,
            f"FPS: {fps:.1f}",
            (panel_x + 14, panel_y + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            fps_color,
            1,
            cv2.LINE_AA,
        )

        # Screen coordinates
        cv2.putText(
            img,
            f"Screen: {screen_pos[0]}, {screen_pos[1]}",
            (panel_x + 14, panel_y + 46),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        # Multi-monitor mode
        mon_text = f"Mode: {self.mon_mgr.mode.upper()}"
        cv2.putText(
            img,
            mon_text,
            (panel_x + 14, panel_y + 68),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (160, 200, 255),
            1,
            cv2.LINE_AA,
        )

    def _draw_footer_bar(
        self,
        img: np.ndarray,
        w: int,
        h: int,
        is_paused: bool,
    ):
        """Draw bottom helper bar with key commands."""
        bar_h = 28
        bar_y = h - bar_h
        cv2.rectangle(img, (0, bar_y), (w, h), (18, 18, 22), -1)

        help_text = "[ESC/Q] Quit  |  [F8/Space] Pause  |  [M] Mode  |  [D] Toggle HUD"
        cv2.putText(
            img,
            help_text,
            (12, h - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )

    def _draw_rounded_card(
        self,
        img: np.ndarray,
        x: int,
        y: int,
        w: int,
        h: int,
        color: Tuple[int, int, int],
        alpha: float = 0.8,
    ):
        """Draw semi-transparent filled rectangle card."""
        sub_img = img[y : y + h, x : x + w]
        rect = np.full(sub_img.shape, color, dtype=np.uint8)
        res = cv2.addWeighted(sub_img, 1.0 - alpha, rect, alpha, 1.0)
        img[y : y + h, x : x + w] = res
        cv2.rectangle(img, (x, y), (x + w, y + h), (60, 60, 70), 1, cv2.LINE_AA)
