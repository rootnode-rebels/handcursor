"""
Configuration parameters for Virtual Hand Cursor.
All dimensions, thresholds, and behavior settings can be tuned here.
"""
import os
import sys
from pathlib import Path

# Paths (Supports both direct python execution and PyInstaller bundled .exe)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = str(BASE_DIR / "hand_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

# Camera Settings
import cv2
CAMERA_ID = 0
CAMERA_BACKEND = cv2.CAP_DSHOW  # DirectShow backend for reliable Windows camera capture
FRAME_WIDTH = 1280              # Maximum HD 720p widescreen resolution for largest control area
FRAME_HEIGHT = 720
TARGET_FPS = 30

# Screen Mapping & Bounding Box (Active Area)
# Margins from camera frame edges (smaller margin = larger control frame area)
MARGIN_X = 60
MARGIN_Y = 40


# Cursor Movement & Stabilization
# Higher smoothing = smoother cursor; lower = more responsive
SMOOTHING_FACTOR = 3
DEADZONE_RADIUS = 5            # Pixels of involuntary hand jitter to ignore when hovering
CLICK_FREEZE_TIME = 0.20       # Seconds to lock/freeze cursor position during click

# Navigation Mode:
# 'relative' (Air Mouse / Touchpad): Keeps cursor in original position when hand appears, moves relative to it, reaches all corners easily.
# 'absolute': Maps camera frame coordinates directly to screen pixels.
CONTROL_MODE = "relative"
MOUSE_SENSITIVITY = 1.6        # Balanced, natural 1:1 speed multiplier (eliminates over-fast / flying cursor)

# Gesture Thresholds (scaled for 1280x720 HD frame)
PINCH_THRESHOLD_CLICK = 65     # Thumb tip to Index tip distance to trigger Left Click
PINCH_THRESHOLD_RIGHT = 70     # Thumb tip to Pinky (small finger) tip distance to trigger Right Click
PINCH_THRESHOLD_RELEASE = 90   # Distance to release pinch state
SCROLL_THRESHOLD = 32          # Minimum finger movement to trigger scroll

# Debounce & Cooldown Timers (in seconds)
CLICK_COOLDOWN = 0.35
RIGHT_CLICK_COOLDOWN = 0.45
SCROLL_COOLDOWN = 0.05

# Hands Configuration
# By default: Right hand controls cursor movement; Left hand controls clicks / actions.
# Single hand fallback automatically activates if only one hand is in camera view.
PRIMARY_CURSOR_HAND = "Right"
PRIMARY_ACTION_HAND = "Left"

# Visual Feedback Colors (BGR format for OpenCV)
COLOR_BOUNDING_BOX = (255, 120, 0)      # Neon Blue
COLOR_RIGHT_HAND = (0, 255, 128)        # Mint Green (Cursor Hand)
COLOR_LEFT_HAND = (255, 0, 128)         # Magenta/Purple (Action Hand)
COLOR_LANDMARK = (0, 255, 255)          # Yellow
COLOR_CONNECTION = (200, 200, 200)      # Light Grey
COLOR_CLICK_ACTIVE = (0, 0, 255)        # Bright Red when clicked
