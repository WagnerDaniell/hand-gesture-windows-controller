"""
Unit and Integration Tests for Hand Gesture Windows Controller.
Verifies math filters, state machine transitions, gesture classification, and monitor mapping.
"""

import sys
import unittest
import numpy as np

from config import AppConfig
from core.smoothing import OneEuroFilter, ExponentialMovingAverage, CursorSmoother
from core.state_machine import GestureState, GestureStateMachine
from vision.hand_detector import HandLandmarks, LandmarkPoint
from vision.gesture_classifier import GestureClassifier
from window_manager.monitor_manager import MonitorManager
from window_manager.window_controller import WindowController


class TestSmoothingFilters(unittest.TestCase):
    """Test jitter suppression and latency characteristics."""

    def test_one_euro_filter_initialization(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.05)
        val1 = f.filter(100.0, timestamp=1.0)
        self.assertEqual(val1, 100.0)
        
        val2 = f.filter(105.0, timestamp=1.033)
        self.assertTrue(100.0 < val2 < 105.0)

    def test_cursor_smoother_deadzone(self):
        smoother = CursorSmoother(deadzone_pixels=2.0)
        p1 = smoother.smooth(500, 500, timestamp=1.0)
        self.assertEqual(p1, (500, 500))

        # Micro movement under 2 pixels should be ignored (deadzone)
        p2 = smoother.smooth(500.5, 500.5, timestamp=1.033)
        self.assertEqual(p2, (500, 500))

        # Larger movement should update position
        p3 = smoother.smooth(550, 550, timestamp=1.066)
        self.assertTrue(p3[0] > 500 and p3[1] > 500)


class TestStateMachine(unittest.TestCase):
    """Test gesture debouncing and mouse event lifecycle."""

    def test_state_transitions(self):
        sm = GestureStateMachine(debounce_frames=2, cooldown_seconds=0.0)
        
        # Frame 1: Candidate Pointing
        r1 = sm.update(GestureState.POINTING)
        # Not confirmed yet (needs 2 frames)
        self.assertEqual(sm.current_state, GestureState.UNKNOWN)

        # Frame 2: Confirmed Pointing
        r2 = sm.update(GestureState.POINTING)
        self.assertEqual(sm.current_state, GestureState.POINTING)
        self.assertEqual(r2["action"], "mouse_move")

        # 2. Transition to CLICK (Single Left Click)
        sm.update(GestureState.CLICK)
        r3 = sm.update(GestureState.CLICK)
        self.assertEqual(sm.current_state, GestureState.CLICK)
        self.assertEqual(r3["action"], "click")
        self.assertFalse(sm.is_mouse_down)

        # 3. Transition to OPEN_HAND (Hold Drag)
        sm.update(GestureState.OPEN_HAND)
        r4 = sm.update(GestureState.OPEN_HAND)
        self.assertEqual(sm.current_state, GestureState.OPEN_HAND)
        self.assertTrue(sm.is_mouse_down)
        self.assertEqual(r4["action"], "mouse_down")

        # 4. Transition back to POINTING (Release Hold)
        sm.update(GestureState.POINTING)
        r6 = sm.update(GestureState.POINTING)
        self.assertEqual(sm.current_state, GestureState.POINTING)
        self.assertFalse(sm.is_mouse_down)
        self.assertEqual(r6["action"], "mouse_up")

    def test_pause_mode(self):
        sm = GestureStateMachine()
        sm.set_pause(True)
        r = sm.update(GestureState.POINTING)
        self.assertTrue(r["is_paused"])
        self.assertEqual(r["state"], GestureState.FIST)


class TestMonitorManager(unittest.TestCase):
    """Test multi-monitor coordinate normalization."""

    def test_coordinate_mapping(self):
        mgr = MonitorManager(mode="span_all")
        
        # Test 0.0 -> left, top
        x_min, y_min = mgr.map_normalized_to_screen(0.0, 0.0)
        self.assertEqual(x_min, mgr.virtual_bounds.left)
        self.assertEqual(y_min, mgr.virtual_bounds.top)

        # Test 1.0 -> right - 1, bottom - 1
        x_max, y_max = mgr.map_normalized_to_screen(1.0, 1.0)
        self.assertEqual(x_max, mgr.virtual_bounds.right - 1)
        self.assertEqual(y_max, mgr.virtual_bounds.bottom - 1)


def make_mock_hand(finger_extension: dict, pinch_dist_norm: float = 0.5) -> HandLandmarks:
    """Generate synthetic 21 landmark points for testing gesture classifier."""
    landmarks = []
    # 0: Wrist at bottom
    landmarks.append(LandmarkPoint(0.5, 0.9, 0.0, 320, 430))

    # Base coords
    # Thumb (1..4)
    landmarks.append(LandmarkPoint(0.45, 0.8, 0.0, 290, 380))
    landmarks.append(LandmarkPoint(0.40, 0.7, 0.0, 260, 330))
    landmarks.append(LandmarkPoint(0.38, 0.65, 0.0, 240, 310))
    
    # Thumb tip position depending on pinch
    if pinch_dist_norm < 0.3:
        # Close to index tip
        landmarks.append(LandmarkPoint(0.44, 0.41, 0.0, 280, 200))
    else:
        landmarks.append(LandmarkPoint(0.30, 0.55, 0.0, 190, 260))

    # Index (5..8)
    landmarks.append(LandmarkPoint(0.45, 0.6, 0.0, 290, 290))
    landmarks.append(LandmarkPoint(0.45, 0.5, 0.0, 290, 240))
    landmarks.append(LandmarkPoint(0.45, 0.45, 0.0, 290, 210))
    if finger_extension.get("index", True):
        landmarks.append(LandmarkPoint(0.45, 0.35, 0.0, 290, 170))  # Extended (Tip far)
    else:
        landmarks.append(LandmarkPoint(0.45, 0.65, 0.0, 290, 310))  # Folded (Tip curled)

    # Middle (9..12)
    landmarks.append(LandmarkPoint(0.50, 0.6, 0.0, 320, 290))
    landmarks.append(LandmarkPoint(0.50, 0.5, 0.0, 320, 240))
    landmarks.append(LandmarkPoint(0.50, 0.45, 0.0, 320, 210))
    if finger_extension.get("middle", False):
        landmarks.append(LandmarkPoint(0.50, 0.32, 0.0, 320, 150))
    else:
        landmarks.append(LandmarkPoint(0.50, 0.65, 0.0, 320, 310))

    # Ring (13..16)
    landmarks.append(LandmarkPoint(0.55, 0.6, 0.0, 350, 290))
    landmarks.append(LandmarkPoint(0.55, 0.5, 0.0, 350, 240))
    landmarks.append(LandmarkPoint(0.55, 0.45, 0.0, 350, 210))
    if finger_extension.get("ring", False):
        landmarks.append(LandmarkPoint(0.55, 0.35, 0.0, 350, 170))
    else:
        landmarks.append(LandmarkPoint(0.55, 0.65, 0.0, 350, 310))

    # Pinky (17..20)
    landmarks.append(LandmarkPoint(0.60, 0.65, 0.0, 380, 310))
    landmarks.append(LandmarkPoint(0.60, 0.55, 0.0, 380, 260))
    landmarks.append(LandmarkPoint(0.60, 0.50, 0.0, 380, 240))
    if finger_extension.get("pinky", False):
        landmarks.append(LandmarkPoint(0.60, 0.40, 0.0, 380, 190))
    else:
        landmarks.append(LandmarkPoint(0.60, 0.65, 0.0, 380, 310))

    return HandLandmarks(
        landmarks=landmarks,
        handedness="Right",
        palm_scale=0.3,
        raw_mp_landmarks=None,
    )


class TestGestureClassifier(unittest.TestCase):
    """Test geometric classification rules."""

    def setUp(self):
        self.classifier = GestureClassifier()

    def test_pointing_classification(self):
        hand = make_mock_hand({"index": True, "middle": False, "ring": False, "pinky": False}, pinch_dist_norm=0.8)
        state, _ = self.classifier.classify(hand)
        self.assertEqual(state, GestureState.POINTING)

    def test_fist_classification(self):
        hand = make_mock_hand({"index": False, "middle": False, "ring": False, "pinky": False}, pinch_dist_norm=0.8)
        state, _ = self.classifier.classify(hand)
        self.assertEqual(state, GestureState.FIST)

    def test_open_hand_classification(self):
        hand = make_mock_hand({"index": True, "middle": True, "ring": True, "pinky": True}, pinch_dist_norm=0.8)
        state, _ = self.classifier.classify(hand)
        self.assertEqual(state, GestureState.OPEN_HAND)

    def test_click_classification_two_fingers(self):
        hand = make_mock_hand({"index": True, "middle": True, "ring": False, "pinky": False}, pinch_dist_norm=0.8)
        state, _ = self.classifier.classify(hand)
        self.assertEqual(state, GestureState.CLICK)

    def test_click_classification_pinch(self):
        hand = make_mock_hand({"index": True, "middle": False, "ring": False, "pinky": False}, pinch_dist_norm=0.2)
        state, _ = self.classifier.classify(hand)
        self.assertEqual(state, GestureState.CLICK)

    def test_window_controller_lookup(self):
        ctrl = WindowController()
        fg = ctrl.get_foreground_window()
        # Foreground window should either be valid WindowInfo or None in headless/test environments
        if fg is not None:
            self.assertIsInstance(fg.hwnd, int)
            self.assertIsInstance(fg.rect, tuple)

    def test_monitor_mode_cycle(self):
        mgr = MonitorManager()
        initial_mode = mgr.mode
        new_mode = mgr.cycle_mode()
        self.assertIn(new_mode, ["span_all", "primary_only", "selected_monitor"])
        self.assertNotEqual(initial_mode, new_mode)


if __name__ == "__main__":
    unittest.main()
