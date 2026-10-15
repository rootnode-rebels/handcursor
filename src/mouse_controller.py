"""
Mouse Controller module using native Windows Win32 API and PyAutoGUI fallback.
Includes:
- Click-Lock Position Freezing (locks cursor in place during click gestures)
- Adaptive Deadzone Filter (eliminates hand micro-tremors when hovering over buttons)
- Speed-Adaptive Exponential Smoothing (snappy when moving, rock-solid when hovering)
"""
import sys
import time
import math
from typing import Optional, Tuple
import numpy as np

IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    user32 = ctypes.windll.user32

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
else:
    user32 = None
    POINT = None

import pyautogui

from src.config import (
    FRAME_WIDTH,
    FRAME_HEIGHT,
    MARGIN_X,
    MARGIN_Y,
    SMOOTHING_FACTOR,
    DEADZONE_RADIUS,
    CLICK_FREEZE_TIME,
    CLICK_COOLDOWN,
    RIGHT_CLICK_COOLDOWN,
    SCROLL_COOLDOWN,
    CONTROL_MODE,
    MOUSE_SENSITIVITY
)
from src.gesture_classifier import GestureAction


class MouseController:
    """Translates normalized camera coordinates and gesture actions into OS mouse events."""

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_WHEEL = 0x0800

    def __init__(self):
        pyautogui.PAUSE = 0.0
        pyautogui.FAILSAFE = False

        if IS_WINDOWS and user32:
            self.screen_width = user32.GetSystemMetrics(0)
            self.screen_height = user32.GetSystemMetrics(1)
        else:
            self.screen_width, self.screen_height = pyautogui.size()

        # Configurable parameters (can be adjusted live via GUI sliders)
        self.control_mode = CONTROL_MODE  # "relative" (Air Mouse) or "absolute"
        self.sensitivity = float(MOUSE_SENSITIVITY)
        self.smoothing_factor = SMOOTHING_FACTOR
        self.deadzone_radius = DEADZONE_RADIUS
        self.click_freeze_time = CLICK_FREEZE_TIME

        # State tracking for smoothing & stabilization
        self.prev_x = self.screen_width // 2
        self.prev_y = self.screen_height // 2

        # Debouncing and stabilization timestamps
        self.last_left_click = 0.0
        self.last_right_click = 0.0
        self.last_scroll = 0.0
        self.last_click_event_time = 0.0

        # Dynamic active area margins (smaller margin = larger control frame area)
        self.margin_x = MARGIN_X
        self.margin_y = MARGIN_Y

        # Relative tracking state (stores previous hand camera coordinate)
        self.prev_hand_x: Optional[int] = None
        self.prev_hand_y: Optional[int] = None

        # Click state indicator
        self.is_left_clicked = False
        self.is_right_clicked = False

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Gets current physical cursor position on the screen."""
        if IS_WINDOWS and user32 and POINT:
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            return int(pt.x), int(pt.y)
        pos = pyautogui.position()
        return int(pos[0]), int(pos[1])


    def map_coordinates(self, camera_x: int, camera_y: int) -> Tuple[int, int]:
        """
        Maps camera coordinates to screen coordinates with:
        - Bounding box margin projection
        - Deadzone tremor cancellation
        - Speed-adaptive smoothing
        """
        # 1. Project within active camera margins
        screen_x = np.interp(
            camera_x,
            [self.margin_x, FRAME_WIDTH - self.margin_x],
            [0, self.screen_width]
        )
        screen_y = np.interp(
            camera_y,
            [self.margin_y, FRAME_HEIGHT - self.margin_y],
            [0, self.screen_height]
        )

        screen_x = int(np.clip(screen_x, 0, self.screen_width - 1))
        screen_y = int(np.clip(screen_y, 0, self.screen_height - 1))

        # 2. Deadzone Filter: ignore involuntary finger twitch when hovering
        delta_dist = math.hypot(screen_x - self.prev_x, screen_y - self.prev_y)
        if delta_dist < self.deadzone_radius:
            return self.prev_x, self.prev_y

        # 3. Adaptive Smoothing:
        if delta_dist > 60:
            adaptive_smoothing = max(2, self.smoothing_factor - 1)
        elif delta_dist < 20:
            adaptive_smoothing = self.smoothing_factor + 3
        else:
            adaptive_smoothing = self.smoothing_factor

        smooth_x = int(self.prev_x + (screen_x - self.prev_x) / adaptive_smoothing)
        smooth_y = int(self.prev_y + (screen_y - self.prev_y) / adaptive_smoothing)

        self.prev_x, self.prev_y = smooth_x, smooth_y
        return smooth_x, smooth_y

    def set_cursor_pos(self, x: int, y: int):
        """Moves cursor across entire desktop via native Win32 API."""
        if IS_WINDOWS and user32:
            user32.SetCursorPos(x, y)
        else:
            pyautogui.moveTo(x, y)

    def trigger_left_click(self):
        """Triggers left click globally across any active application."""
        if IS_WINDOWS and user32:
            user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.click()

    def trigger_right_click(self):
        """Triggers right click globally across any active application."""
        if IS_WINDOWS and user32:
            user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        else:
            pyautogui.rightClick()

    def trigger_scroll(self, amount: int):
        """Scrolls vertically across any active application."""
        if IS_WINDOWS and user32:
            user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
        else:
            pyautogui.scroll(amount)

    def execute_action(
        self,
        cursor_pos: Optional[Tuple[int, int]],
        action: GestureAction
    ) -> Tuple[Optional[Tuple[int, int]], bool]:
        """
        Executes OS mouse action according to gesture.
        In Relative Mode: Anchors to current physical cursor position on hand entry (NO JUMP),
        and applies dynamic speed curve to reach all screen corners effortlessly.
        Locks cursor position during and immediately after a click to eliminate click jitter.
        """
        current_time = time.time()
        self.is_left_clicked = False
        self.is_right_clicked = False
        target_screen_pos = None

        is_clicking_gesture = action in (GestureAction.LEFT_CLICK, GestureAction.RIGHT_CLICK)
        is_in_click_freeze = (current_time - self.last_click_event_time) < self.click_freeze_time

        # 1. Update cursor position
        if cursor_pos is None:
            # Hand is NOT visible: reset relative tracking anchor so it doesn't jump when re-entering
            self.prev_hand_x = None
            self.prev_hand_y = None
            if is_in_click_freeze:
                target_screen_pos = (self.prev_x, self.prev_y)
        else:
            if is_clicking_gesture or is_in_click_freeze:
                # FREEZE position at target button during click!
                target_screen_pos = (self.prev_x, self.prev_y)
                # Keep hand coordinate anchor updated so releasing freeze does not cause sudden jump
                self.prev_hand_x = cursor_pos[0]
                self.prev_hand_y = cursor_pos[1]
            elif self.control_mode == "relative":
                # RELATIVE / TOUCHPAD / AIR-MOUSE MODE
                # If hand JUST appeared, keep cursor in current position (NO JUMP!)
                if self.prev_hand_x is None or self.prev_hand_y is None:
                    cur_x, cur_y = self.get_cursor_pos()
                    self.prev_x = cur_x
                    self.prev_y = cur_y
                    self.prev_hand_x = cursor_pos[0]
                    self.prev_hand_y = cursor_pos[1]
                    target_screen_pos = (cur_x, cur_y)
                else:
                    # Hand delta in camera coordinates
                    dx = cursor_pos[0] - self.prev_hand_x
                    dy = cursor_pos[1] - self.prev_hand_y
                    self.prev_hand_x = cursor_pos[0]
                    self.prev_hand_y = cursor_pos[1]

                    # Filter out sub-pixel sensor noise
                    dist_hand = math.hypot(dx, dy)
                    if dist_hand < 1.0:
                        dx, dy = 0.0, 0.0

                    # Dynamic speed curve: gentle hand movement gives fine precision,
                    # faster hand flick gives quick screen-spanning traversal to reach any corner
                    speed_boost = 1.0 + min(1.8, dist_hand / 25.0)
                    target_x = self.prev_x + dx * self.sensitivity * speed_boost
                    target_y = self.prev_y + dy * self.sensitivity * speed_boost

                    # Clamp strictly to screen dimensions
                    target_x = max(0, min(self.screen_width - 1, target_x))
                    target_y = max(0, min(self.screen_height - 1, target_y))

                    # Tremor deadzone & smoothing
                    delta_dist = math.hypot(target_x - self.prev_x, target_y - self.prev_y)
                    if delta_dist < self.deadzone_radius:
                        smooth_x, smooth_y = self.prev_x, self.prev_y
                    else:
                        adaptive_factor = max(1.2, float(self.smoothing_factor) * (0.6 if delta_dist > 35 else 1.0))
                        smooth_x = int(self.prev_x + (target_x - self.prev_x) / adaptive_factor)
                        smooth_y = int(self.prev_y + (target_y - self.prev_y) / adaptive_factor)

                    self.prev_x, self.prev_y = smooth_x, smooth_y
                    target_screen_pos = (smooth_x, smooth_y)
                    try:
                        self.set_cursor_pos(smooth_x, smooth_y)
                    except Exception:
                        pass
            else:
                # ABSOLUTE MODE (Direct camera-to-screen mapping)
                smooth_x, smooth_y = self.map_coordinates(cursor_pos[0], cursor_pos[1])
                target_screen_pos = (smooth_x, smooth_y)
                try:
                    self.set_cursor_pos(smooth_x, smooth_y)
                except Exception:
                    pass

        # 2. Execute discrete gesture actions
        if action == GestureAction.LEFT_CLICK:
            if current_time - self.last_left_click > CLICK_COOLDOWN:
                self.last_click_event_time = current_time
                self.trigger_left_click()
                self.last_left_click = current_time
                self.is_left_clicked = True
                return target_screen_pos, True

        elif action == GestureAction.RIGHT_CLICK:
            if current_time - self.last_right_click > RIGHT_CLICK_COOLDOWN:
                self.last_click_event_time = current_time
                self.trigger_right_click()
                self.last_right_click = current_time
                self.is_right_clicked = True
                return target_screen_pos, True

        elif action == GestureAction.SCROLL_UP:
            if current_time - self.last_scroll > SCROLL_COOLDOWN:
                self.trigger_scroll(120)
                self.last_scroll = current_time
                return target_screen_pos, True

        elif action == GestureAction.SCROLL_DOWN:
            if current_time - self.last_scroll > SCROLL_COOLDOWN:
                self.trigger_scroll(-120)
                self.last_scroll = current_time
                return target_screen_pos, True

        return target_screen_pos, False
