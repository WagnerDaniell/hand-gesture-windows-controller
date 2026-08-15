"""
Robust Geometric Gesture Classifier.
Accurately recognizes Pointing, Pinch/Drag, Open Hand, Closed Fist with distance normalization.
"""

import math
from typing import Dict, Tuple
from core.state_machine import GestureState
from vision.hand_detector import HandLandmarks


class GestureClassifier:
    """
    Classifies 3D hand poses into discrete user gestures with scale-invariance and hysteresis.
    """

    def __init__(
        self,
        pinch_threshold: float = 0.32,
        pinch_release_threshold: float = 0.45,
    ):
        self.pinch_threshold = pinch_threshold
        self.pinch_release_threshold = pinch_release_threshold
        self.was_pinching = False

    def classify(self, hand: HandLandmarks) -> Tuple[GestureState, Dict[str, any]]:
        """
        Evaluate hand landmarks and return the current gesture state and debug metrics.
        """
        lm = hand.landmarks
        palm_scale = hand.palm_scale
        wrist = lm[0]

        # Evaluate individual finger extension states (True = Extended, False = Folded)
        fingers_extended = self._get_fingers_extended(hand)

        thumb_open = fingers_extended["thumb"]
        index_open = fingers_extended["index"]
        middle_open = fingers_extended["middle"]
        ring_open = fingers_extended["ring"]
        pinky_open = fingers_extended["pinky"]

        # Calculate Normalized Pinch Distance (Thumb Tip [4] to Index Tip [8])
        thumb_tip = lm[4]
        index_tip = lm[8]
        raw_pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
        norm_pinch_dist = raw_pinch_dist / palm_scale

        # Dynamic Hysteresis for Pinch State
        current_pinch_threshold = (
            self.pinch_release_threshold if self.was_pinching else self.pinch_threshold
        )
        is_pinching = norm_pinch_dist < current_pinch_threshold
        self.was_pinching = is_pinching

        # Classification Hierarchy:
        
        # 1. PINCH / DRAG: Thumb and Index are close together
        # (Allows dragging a window or clicking with precision)
        if is_pinching:
            # Pinch is active if thumb and index tips are pinched
            detected_state = GestureState.PINCH_DRAG

        # 2. CLOSED FIST: All 4 non-thumb fingers are folded, thumb is folded or neutral
        elif (not index_open) and (not middle_open) and (not ring_open) and (not pinky_open):
            detected_state = GestureState.FIST

        # 3. OPEN HAND: All 5 fingers (or at least 4 main fingers) extended
        elif index_open and middle_open and ring_open and pinky_open:
            detected_state = GestureState.OPEN_HAND

        # 4. POINTING / CURSOR CONTROL: Index is extended, middle/ring/pinky folded
        elif index_open and (not middle_open) and (not ring_open) and (not pinky_open):
            detected_state = GestureState.POINTING

        # 5. Hybrid pointing with thumb extended
        elif index_open and (not middle_open) and (not ring_open) and (not pinky_open):
            detected_state = GestureState.POINTING

        # Fallback / Intermediate pose
        else:
            # If index is open and ring/pinky closed (e.g. index+middle or slight relaxed hand), default to pointing
            if index_open and (not ring_open) and (not pinky_open):
                detected_state = GestureState.POINTING
            else:
                detected_state = GestureState.UNKNOWN

        metrics = {
            "norm_pinch_dist": norm_pinch_dist,
            "is_pinching": is_pinching,
            "fingers_extended": fingers_extended,
            "palm_scale": palm_scale,
            "handedness": hand.handedness,
        }

        return detected_state, metrics

    def _get_fingers_extended(self, hand: HandLandmarks) -> Dict[str, bool]:
        """Determine extension status for each finger using vector and distance analysis."""
        lm = hand.landmarks
        wrist = lm[0]

        # For Index, Middle, Ring, Pinky:
        # A finger is extended if Tip distance to wrist > PIP distance to wrist
        # AND Tip is geometrically further along the finger axis than DIP.
        finger_indices = {
            "index": (5, 6, 7, 8),     # MCP, PIP, DIP, TIP
            "middle": (9, 10, 11, 12),
            "ring": (13, 14, 15, 16),
            "pinky": (17, 18, 19, 20),
        }

        extended_status = {}

        for name, (mcp_idx, pip_idx, dip_idx, tip_idx) in finger_indices.items():
            mcp = lm[mcp_idx]
            pip = lm[pip_idx]
            tip = lm[tip_idx]

            dist_tip_wrist = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
            dist_pip_wrist = math.hypot(pip.x - wrist.x, pip.y - wrist.y)
            dist_tip_mcp = math.hypot(tip.x - mcp.x, tip.y - mcp.y)
            dist_pip_mcp = math.hypot(pip.x - mcp.x, pip.y - mcp.y)

            # Extended if Tip is clearly further from wrist and MCP than the PIP joint
            is_extended = (dist_tip_wrist > dist_pip_wrist * 1.1) and (dist_tip_mcp > dist_pip_mcp * 1.1)
            extended_status[name] = is_extended

        # Thumb analysis (Thumb CMC 1, MCP 2, IP 3, TIP 4)
        # Thumb is extended if Thumb TIP is further from Pinky MCP (17) than Thumb IP (3) is.
        thumb_tip = lm[4]
        thumb_ip = lm[3]
        pinky_mcp = lm[17]

        dist_thumb_tip_pinky = math.hypot(thumb_tip.x - pinky_mcp.x, thumb_tip.y - pinky_mcp.y)
        dist_thumb_ip_pinky = math.hypot(thumb_ip.x - pinky_mcp.x, thumb_ip.y - pinky_mcp.y)
        extended_status["thumb"] = dist_thumb_tip_pinky > (dist_thumb_ip_pinky * 1.05)

        return extended_status

    def reset(self):
        """Reset hysteresis state."""
        self.was_pinching = False
