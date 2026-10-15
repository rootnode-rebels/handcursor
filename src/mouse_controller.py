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
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    user32 = ctypes.windll.user32
else:
    user32 = None

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
    SCROLL_COOLDOWN
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

        # Click state indicator
        self.is_left_clicked = False
        self.is_right_clicked = False

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
        Locks cursor position during and immediately after a click to eliminate click jitter.
        """
        current_time = time.time()
        self.is_left_clicked = False
        self.is_right_clicked = False
        target_screen_pos = None

        is_clicking_gesture = action in (GestureAction.LEFT_CLICK, GestureAction.RIGHT_CLICK)
        is_in_click_freeze = (current_time - self.last_click_event_time) < CLICK_FREEZE_TIME

        # 1. Update cursor position (FREEZE if currently clicking or just clicked)
        if cursor_pos is not None:
            if is_clicking_gesture or is_in_click_freeze:
                # FREEZE position at target button! Do not move cursor during click!
                target_screen_pos = (self.prev_x, self.prev_y)
            else:
                smooth_x, smooth_y = self.map_coordinates(cursor_pos[0], cursor_pos[1])
                target_screen_pos = (smooth_x, smooth_y)
                try:
                    self.set_cursor_pos(smooth_x, smooth_y)
                except Exception:
                    pass
        elif is_in_click_freeze:
            target_screen_pos = (self.prev_x, self.prev_y)

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
