"""
MediaPipe Hand Detector and Landmark Processor.
Handles camera frame processing, hand landmark extraction, and spatial scaling.
"""

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os


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
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.70,
        min_tracking_confidence: float = 0.70,
        model_complexity: int = 1,
    ):
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'hand_landmarker.task')
        
        with open(model_path, 'rb') as f:
            model_data = f.read()
            
        base_options = python.BaseOptions(model_asset_buffer=model_data)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        # Standard mediapipe hand connections
        self.HAND_CONNECTIONS = frozenset([
            (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
            (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
            (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
        ])

    def process_hands(self, frame_bgr: np.ndarray) -> List[HandLandmarks]:
        """
        Process a BGR video frame and extract all detected hand landmarks (up to 2).
        Returns a list of HandLandmarks instances.
        """
        frame_h, frame_w, _ = frame_bgr.shape
        
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        results = self.detector.detect(mp_image)

        if not results.hand_landmarks:
            return []

        hands_list: List[HandLandmarks] = []
        for i, mp_hand_landmarks in enumerate(results.hand_landmarks):
            handedness = "Right"
            if results.handedness and i < len(results.handedness) and len(results.handedness[i]) > 0:
                handedness = results.handedness[i][0].category_name

            # Parse 21 landmarks
            parsed_landmarks: List[LandmarkPoint] = []
            for lm in mp_hand_landmarks:
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

            # Palm scale
            wrist = parsed_landmarks[0]
            middle_mcp = parsed_landmarks[9]
            palm_scale = math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y)
            if palm_scale <= 1e-4:
                palm_scale = 0.2

            hands_list.append(
                HandLandmarks(
                    landmarks=parsed_landmarks,
                    handedness=handedness,
                    palm_scale=palm_scale,
                    raw_mp_landmarks=mp_hand_landmarks,
                )
            )

        return hands_list

    def process_frame(self, frame_bgr: np.ndarray) -> Optional[HandLandmarks]:
        """Backward compatible single hand extractor."""
        hands = self.process_hands(frame_bgr)
        return hands[0] if hands else None

    def draw_landmarks(
        self,
        frame: np.ndarray,
        hand_landmarks: HandLandmarks,
        color_custom: Optional[Tuple[int, int, int]] = None,
    ):
        """Draw styled landmarks and skeletal connections on frame."""
        if not hand_landmarks:
            return
            
        color_conn = color_custom if color_custom else (0, 255, 0)
        color_lm = (0, 0, 255) if not color_custom else color_custom
        
        # Draw connections
        for connection in self.HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            p1 = hand_landmarks.landmarks[start_idx]
            p2 = hand_landmarks.landmarks[end_idx]
            
            cv2.line(frame, (p1.px, p1.py), (p2.px, p2.py), color_conn, 2)
            
        # Draw landmarks
        for lm in hand_landmarks.landmarks:
            cv2.circle(frame, (lm.px, lm.py), 4, color_lm, -1)

    def close(self):
        """Release MediaPipe resources."""
        if self.detector:
            self.detector.close()
