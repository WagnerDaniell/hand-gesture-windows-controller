"""
MediaPipe Hand Detector and Landmark Processor.
Handles camera frame processing, hand landmark extraction, and spatial scaling.
"""

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np


@dataclass
class LandmarkPoint:
    """Single 3D landmark representation."""
    x: float      # Normalized [0.0, 1.0]
    y: float      # Normalized [0.0, 1.0]
    z: float      # Depth relative to wrist
    px: int       # Pixel X coordinate in frame
    py: int       # Pixel Y coordinate in frame


@dataclass
class HandLandmarks:
    """Full hand detection data container."""
    landmarks: List[LandmarkPoint]
    handedness: str           # "Left" or "Right"
    palm_scale: float         # Distance between Wrist (0) and Middle MCP (9)
    raw_mp_landmarks: any     # MediaPipe raw landmark object for drawing


class HandDetector:
    """
    Wraps Google MediaPipe Hands with real-time video stream optimizations.
    """

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.70,
        min_tracking_confidence: float = 0.70,
        model_complexity: int = 1,
    ):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity,
        )

    def process_frame(self, frame_bgr: np.ndarray) -> Optional[HandLandmarks]:
        """
        Process a BGR video frame and extract hand landmarks.
        Returns HandLandmarks instance for the primary hand, or None if no hand detected.
        """
        frame_h, frame_w, _ = frame_bgr.shape
        
        # Convert BGR to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        results = self.hands.process(frame_rgb)
        frame_rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            return None

        # Prioritize the first detected hand
        mp_hand_landmarks = results.multi_hand_landmarks[0]
        
        # Determine handedness if available
        handedness = "Right"
        if results.multi_handedness and len(results.multi_handedness) > 0:
            handedness = results.multi_handedness[0].classification[0].label

        # Parse 21 landmarks
        parsed_landmarks: List[LandmarkPoint] = []
        for lm in mp_hand_landmarks.landmark:
            px = int(lm.x * frame_w)
            py = int(lm.y * frame_h)
            parsed_landmarks.append(
                LandmarkPoint(
                    x=float(lm.x),
                    y=float(lm.y),
                    z=float(lm.z),
                    px=px,
                    py=py,
                )
            )

        # Calculate palm scale (Euclidean distance between Wrist (0) and Middle MCP (9))
        wrist = parsed_landmarks[0]
        middle_mcp = parsed_landmarks[9]
        palm_scale = math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y)
        if palm_scale <= 1e-4:
            palm_scale = 0.2  # Safe fallback

        return HandLandmarks(
            landmarks=parsed_landmarks,
            handedness=handedness,
            palm_scale=palm_scale,
            raw_mp_landmarks=mp_hand_landmarks,
        )

    def draw_landmarks(
        self,
        frame: np.ndarray,
        hand_landmarks: HandLandmarks,
        color_custom: Optional[Tuple[int, int, int]] = None,
    ):
        """Draw styled landmarks and skeletal connections on frame."""
        if hand_landmarks and hand_landmarks.raw_mp_landmarks:
            self.mp_drawing.draw_landmarks(
                frame,
                hand_landmarks.raw_mp_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style(),
            )

    def close(self):
        """Release MediaPipe resources."""
        if self.hands:
            self.hands.close()
