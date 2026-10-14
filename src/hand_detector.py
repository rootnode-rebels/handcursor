"""
Hand detection and landmark tracking module using MediaPipe Tasks Vision.
Tracks up to 2 hands in real-time, extracts 21 3D landmarks per hand,
and provides helper methods for finger status and distances.
"""
import os
import math
import urllib.request
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np

# Ensure matplotlib import in MediaPipe's unused drawing_utils succeeds without bloat
import sys
import types
class _DummyModule(types.ModuleType):
    def __getattr__(self, name): return _DummyModule(name)
    def __call__(self, *args, **kwargs): return _DummyModule("dummy")
for _mod in ("matplotlib", "matplotlib.pyplot"):
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except ImportError:
            sys.modules[_mod] = _DummyModule(_mod)

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


from src.config import MODEL_PATH, MODEL_URL


def ensure_model_exists():
    """Ensure the hand landmark model file exists, download if missing."""
    if not os.path.exists(MODEL_PATH):
        print(f"Hand landmark model not found at {MODEL_PATH}.")
        print(f"Downloading model from {MODEL_URL}...")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded successfully.")


class HandDetector:
    """Detects hands and extracts landmark coordinates using MediaPipe."""

    def __init__(self, max_hands: int = 2, min_detection_confidence: float = 0.6, min_tracking_confidence: float = 0.5):
        ensure_model_exists()
        
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def find_hands(self, frame: np.ndarray) -> List[Dict]:
        """
        Processes a BGR image frame and returns a list of detected hand dictionaries.
        Each hand dictionary contains:
          - 'label': 'Left' or 'Right'
          - 'score': confidence score
          - 'landmarks': List of (x_px, y_px, z) for 21 points
          - 'norm_landmarks': List of (norm_x, norm_y, norm_z)
          - 'bbox': (x_min, y_min, width, height)
        """
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        detection_result = self.landmarker.detect(mp_image)
        hands = []

        if detection_result.hand_landmarks:
            for i, hand_lms in enumerate(detection_result.hand_landmarks):
                # Handedness category
                handedness_category = detection_result.handedness[i][0]
                label = handedness_category.category_name
                score = handedness_category.score

                # Extract pixel & normalized coords
                px_landmarks = []
                norm_landmarks = []
                x_coords = []
                y_coords = []

                for lm in hand_lms:
                    px_x = int(lm.x * w)
                    px_y = int(lm.y * h)
                    px_landmarks.append((px_x, px_y, lm.z))
                    norm_landmarks.append((lm.x, lm.y, lm.z))
                    x_coords.append(px_x)
                    y_coords.append(px_y)

                # Bounding box
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

                hands.append({
                    "label": label,
                    "score": score,
                    "landmarks": px_landmarks,
                    "norm_landmarks": norm_landmarks,
                    "bbox": bbox
                })

        return hands

    @staticmethod
    def fingers_up(hand_dict: Dict) -> List[bool]:
        """
        Determines which fingers are open/extended.
        Returns [thumb, index, middle, ring, pinky] as booleans.
        """
        lms = hand_dict["landmarks"]
        fingers = []

        # Thumb: compare distance between Thumb tip (4) and Pinky MCP (17)
        # vs Thumb IP (3) and Pinky MCP (17)
        d_thumb_tip_pinky = math.hypot(lms[4][0] - lms[17][0], lms[4][1] - lms[17][1])
        d_thumb_ip_pinky = math.hypot(lms[3][0] - lms[17][0], lms[3][1] - lms[17][1])
        fingers.append(d_thumb_tip_pinky > d_thumb_ip_pinky * 1.15)

        # 4 Fingers: Check if tip y is higher (lower value in pixel space) than PIP joint
        # Index: 8 vs 6
        fingers.append(lms[8][1] < lms[6][1])
        # Middle: 12 vs 10
        fingers.append(lms[12][1] < lms[10][1])
        # Ring: 16 vs 14
        fingers.append(lms[16][1] < lms[14][1])
        # Pinky: 20 vs 18
        fingers.append(lms[20][1] < lms[18][1])

        return fingers

    @staticmethod
    def calculate_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Euclidean distance between two 2D points."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def close(self):
        """Release MediaPipe resources."""
        if hasattr(self, "landmarker"):
            self.landmarker.close()
