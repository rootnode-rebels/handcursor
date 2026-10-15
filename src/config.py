"""
Configuration parameters for AI Virtual Hand Cursor.
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
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# Screen Mapping & Bounding Box (Active Area)
# Margins from camera frame edges (smaller margin = larger control frame area)
MARGIN_X = 50
MARGIN_Y = 40


# Cursor Movement & Stabilization
# Higher smoothing = smoother cursor; lower = more responsive
SMOOTHING_FACTOR = 4
DEADZONE_RADIUS = 8            # Pixels of involuntary hand jitter to ignore when hovering
CLICK_FREEZE_TIME = 0.35       # Seconds to lock/freeze cursor position during and immediately after a click

# Navigation Mode:
# 'relative' (Air Mouse / Touchpad): Keeps cursor in original position when hand appears, moves relative to it, reaches all corners easily.
# 'absolute': Maps camera frame coordinates directly to screen pixels.
CONTROL_MODE = "relative"
MOUSE_SENSITIVITY = 2.2        # Movement multiplier for relative mode

# Gesture Thresholds (in pixels for 640x480 frame)
PINCH_THRESHOLD_CLICK = 38     # Thumb tip to Index tip distance to trigger Left Click
PINCH_THRESHOLD_RIGHT = 38     # Thumb tip to Middle tip distance to trigger Right Click
PINCH_THRESHOLD_RELEASE = 50   # Distance to release pinch state
SCROLL_THRESHOLD = 20          # Minimum finger movement to trigger scroll

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
