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
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
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
from src.filter import PointFilter2D


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

        self.screen_x = 0
        self.screen_y = 0
        self.screen_width = 1920
        self.screen_height = 1080
        self.update_screen_metrics()

        # Configurable parameters (can be adjusted live via GUI sliders)
        self.control_mode = CONTROL_MODE  # "relative" (Air Mouse) or "absolute"
        self.sensitivity = float(MOUSE_SENSITIVITY)
        self.smoothing_factor = SMOOTHING_FACTOR
        self.deadzone_radius = DEADZONE_RADIUS
        self.click_freeze_time = CLICK_FREEZE_TIME

        # State tracking for smoothing & stabilization
        self.prev_x = self.screen_width // 2
        self.prev_y = self.screen_height // 2
        self.curr_screen_x = float(self.prev_x)
        self.curr_screen_y = float(self.prev_y)

        # 1 Euro Filter for camera input stabilization (tuned for ultra-smooth jitter-free tracking)
        self.input_filter = PointFilter2D(min_cutoff=1.0, beta=0.02, d_cutoff=1.0)

        # Velocity tracking for smooth continuous acceleration
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.rel_deadzone = 0.40  # Normalized pixels deadzone to cancel hovering tremor

        # Debouncing, drag and stabilization timestamps
        self.last_left_click = 0.0
        self.last_right_click = 0.0
        self.last_scroll = 0.0
        self.last_click_event_time = 0.0
        self.is_dragging = False
        self.pinch_start_time = 0.0
        self.pinch_start_pos = (self.prev_x, self.prev_y)

        # Dynamic active area margins (smaller margin = larger control frame area)
        self.margin_x = MARGIN_X
        self.margin_y = MARGIN_Y

        # Relative tracking state (stores previous hand camera coordinate)
        self.prev_hand_x: Optional[float] = None
        self.prev_hand_y: Optional[float] = None

        # Click state indicator
        self.is_left_clicked = False
        self.is_right_clicked = False

    def update_screen_metrics(self):
        """Updates screen bounds to adapt dynamically to high-DPI scaling and multi-monitor setups."""
        if IS_WINDOWS and user32:
            try:
                user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                pass
            vw = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            vh = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            if vw > 0 and vh > 0:
                self.screen_x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
                self.screen_y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
                self.screen_width = vw
                self.screen_height = vh
            else:
                self.screen_x = 0
                self.screen_y = 0
                self.screen_width = user32.GetSystemMetrics(0)
                self.screen_height = user32.GetSystemMetrics(1)
        else:
            self.screen_x = 0
            self.screen_y = 0
            self.screen_width, self.screen_height = pyautogui.size()

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
        - Bounding box margin projection across the full virtual desktop
        - Edge and corner accessibility (boundaries never blocked by deadzone)
        - Deadzone tremor cancellation during mid-screen hovering
        - Speed-adaptive smoothing
        """
        min_x = self.screen_x
        max_x = self.screen_x + self.screen_width - 1
        min_y = self.screen_y
        max_y = self.screen_y + self.screen_height - 1

        # 1. Project within active camera margins across entire screen area
        screen_x = np.interp(
            camera_x,
            [self.margin_x, FRAME_WIDTH - self.margin_x],
            [min_x, max_x]
        )
        screen_y = np.interp(
            camera_y,
            [self.margin_y, FRAME_HEIGHT - self.margin_y],
            [min_y, max_y]
        )

        screen_x = int(round(np.clip(screen_x, min_x, max_x)))
        screen_y = int(round(np.clip(screen_y, min_y, max_y)))

        # 2. Deadzone Tremor Filter: ignore involuntary finger twitch when hovering,
        # but NEVER prevent the user from reaching the exact screen corners and borders!
        delta_dist = math.hypot(screen_x - self.prev_x, screen_y - self.prev_y)
        is_at_boundary = (screen_x <= min_x or screen_x >= max_x or screen_y <= min_y or screen_y >= max_y)

        if delta_dist < self.deadzone_radius and not is_at_boundary:
            return self.prev_x, self.prev_y

        # 3. Adaptive Smoothing: snap cleanly to boundaries when hand touches active margin
        if is_at_boundary and delta_dist <= 12:
            smooth_x = screen_x
            smooth_y = screen_y
        else:
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

    def mouse_down_left(self):
        """Presses and holds the left mouse button down."""
        if IS_WINDOWS and user32:
            user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        else:
            pyautogui.mouseDown()

    def mouse_up_left(self):
        """Releases the held left mouse button."""
        if IS_WINDOWS and user32:
            user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.mouseUp()

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

    def _update_position(self, cam_x: float, cam_y: float) -> Tuple[int, int]:
        """Calculates and updates screen position with precision float accumulation, soft-knee deadzone, and velocity smoothing."""
        if self.control_mode == "relative":
            if self.prev_hand_x is None or self.prev_hand_y is None:
                cur_x, cur_y = self.get_cursor_pos()
                self.curr_screen_x = float(cur_x)
                self.curr_screen_y = float(cur_y)
                self.prev_x = cur_x
                self.prev_y = cur_y
                self.prev_hand_x = cam_x
                self.prev_hand_y = cam_y
                self.vel_x = 0.0
                self.vel_y = 0.0
                return (cur_x, cur_y)

            dx = cam_x - self.prev_hand_x
            dy = cam_y - self.prev_hand_y
            self.prev_hand_x = cam_x
            self.prev_hand_y = cam_y

            # Normalize hand displacement relative to standard base resolution
            res_scale_x = max(1.0, FRAME_WIDTH / 640.0)
            res_scale_y = max(1.0, FRAME_HEIGHT / 480.0)
            norm_dx = dx / res_scale_x
            norm_dy = dy / res_scale_y
            dist_hand = math.hypot(norm_dx, norm_dy)

            # Soft-knee deadzone: completely eliminates hovering tremor while easing in motion smoothly
            if dist_hand <= self.rel_deadzone:
                self.vel_x *= 0.35
                self.vel_y *= 0.35
                if math.hypot(self.vel_x, self.vel_y) < 0.05:
                    self.vel_x = 0.0
                    self.vel_y = 0.0
                    return (self.prev_x, self.prev_y)
                target_step_x = 0.0
                target_step_y = 0.0
            else:
                # Smoothstep transition over [rel_deadzone, rel_deadzone + 1.2]: zero sudden jump on start
                t_ease = min(1.0, (dist_hand - self.rel_deadzone) / 1.2)
                soft_gain = t_ease * t_ease * (3.0 - 2.0 * t_ease)

                # Natural velocity curve (smooth, 1:1 control with comfortable speedup on sweeps)
                if dist_hand < 3.0:
                    speed_mult = 0.85 + (dist_hand / 3.0) * 0.20
                elif dist_hand < 12.0:
                    speed_mult = 1.05 + ((dist_hand - 3.0) / 9.0) * 0.35
                else:
                    speed_mult = 1.40 + min(0.45, (dist_hand - 12.0) / 12.0)

                target_step_x = norm_dx * self.sensitivity * speed_mult * soft_gain
                target_step_y = norm_dy * self.sensitivity * speed_mult * soft_gain

            # Adaptive velocity smoothing: eliminates frame-to-frame delta flutter
            smooth_blend = 1.0 / (1.0 + 0.12 * max(1, self.smoothing_factor))
            if dist_hand > 10.0:
                smooth_blend = min(0.95, smooth_blend + 0.25)

            self.vel_x = smooth_blend * target_step_x + (1.0 - smooth_blend) * self.vel_x
            self.vel_y = smooth_blend * target_step_y + (1.0 - smooth_blend) * self.vel_y

            # Float accumulation eliminates integer truncation jitter
            self.curr_screen_x += self.vel_x
            self.curr_screen_y += self.vel_y

            # Clamp strictly to full screen/virtual desktop bounds
            min_x = float(self.screen_x)
            max_x = float(self.screen_x + self.screen_width - 1)
            min_y = float(self.screen_y)
            max_y = float(self.screen_y + self.screen_height - 1)
            self.curr_screen_x = max(min_x, min(max_x, self.curr_screen_x))
            self.curr_screen_y = max(min_y, min(max_y, self.curr_screen_y))

            out_x = int(round(self.curr_screen_x))
            out_y = int(round(self.curr_screen_y))

            self.prev_x = out_x
            self.prev_y = out_y
            try:
                self.set_cursor_pos(out_x, out_y)
            except Exception:
                pass
            return (out_x, out_y)
        else:
            # Absolute mode
            smooth_x, smooth_y = self.map_coordinates(int(round(cam_x)), int(round(cam_y)))
            self.curr_screen_x = float(smooth_x)
            self.curr_screen_y = float(smooth_y)
            try:
                self.set_cursor_pos(smooth_x, smooth_y)
            except Exception:
                pass
            return (smooth_x, smooth_y)

    def execute_action(
        self,
        cursor_pos: Optional[Tuple[int, int]],
        action: GestureAction,
        timestamp: Optional[float] = None
    ) -> Tuple[Optional[Tuple[int, int]], bool]:
        """
        Executes OS mouse action according to gesture.
        - PointFilter2D (1 Euro Filter) stabilizes camera coordinates.
        - Sub-pixel float accumulator provides buttery-smooth tracking.
        - Supports True Drag & Drop and Text Selection (hold pinch to drag, release to drop).
        """
        current_time = time.time() if timestamp is None else float(timestamp)
        self.is_left_clicked = False
        self.is_right_clicked = False
        target_screen_pos = None

        if cursor_pos is None:
            # Hand leaves camera view: release any held drag and reset filters
            if self.is_dragging:
                self.mouse_up_left()
                self.is_dragging = False
            self.input_filter.reset()
            self.prev_hand_x = None
            self.prev_hand_y = None
            self.vel_x = 0.0
            self.vel_y = 0.0
            return (self.prev_x, self.prev_y), False

        # Filter raw camera coordinates through 1 Euro Filter
        filtered_cam_x, filtered_cam_y = self.input_filter.filter(
            float(cursor_pos[0]),
            float(cursor_pos[1]),
            current_time
        )

        # 1. SMART DRAG & CLICK HANDLING
        if action == GestureAction.LEFT_CLICK:
            self.is_left_clicked = True
            if not self.is_dragging:
                self.is_dragging = True
                self.pinch_start_time = current_time
                self.pinch_start_pos = (self.prev_x, self.prev_y)
                self.mouse_down_left()
                self.last_left_click = current_time
                self.last_click_event_time = current_time

            pinch_duration = current_time - self.pinch_start_time
            drag_dist = math.hypot(
                self.curr_screen_x - self.pinch_start_pos[0],
                self.curr_screen_y - self.pinch_start_pos[1]
            )

            # Lock cursor firmly on target element during click gesture.
            # Only start dragging if hand moves deliberately beyond drag deadzone (> 18px).
            if drag_dist < 18.0:
                target_screen_pos = (self.pinch_start_pos[0], self.pinch_start_pos[1])
                self.prev_hand_x = filtered_cam_x
                self.prev_hand_y = filtered_cam_y
                self.vel_x = 0.0
                self.vel_y = 0.0
            else:
                # Dragging while holding button down (selecting text, dragging window)
                target_screen_pos = self._update_position(filtered_cam_x, filtered_cam_y)
            return target_screen_pos, True

        else:
            # Pinch released: end any ongoing drag
            if self.is_dragging:
                self.mouse_up_left()
                self.is_dragging = False
                self.last_click_event_time = current_time
                target_screen_pos = (self.prev_x, self.prev_y)
                self.prev_hand_x = filtered_cam_x
                self.prev_hand_y = filtered_cam_y

        # 2. DISCRETE GESTURE ACTIONS
        if action == GestureAction.RIGHT_CLICK:
            target_screen_pos = (self.prev_x, self.prev_y)
            self.prev_hand_x = filtered_cam_x
            self.prev_hand_y = filtered_cam_y
            self.vel_x = 0.0
            self.vel_y = 0.0
            if current_time - self.last_right_click > RIGHT_CLICK_COOLDOWN:
                self.trigger_right_click()
                self.last_right_click = current_time
                self.is_right_clicked = True
                self.last_click_event_time = current_time
                return target_screen_pos, True

        elif action == GestureAction.SCROLL_UP:
            if current_time - self.last_scroll > SCROLL_COOLDOWN:
                self.trigger_scroll(120)
                self.last_scroll = current_time
                target_screen_pos = (self.prev_x, self.prev_y)
                return target_screen_pos, True

        elif action == GestureAction.SCROLL_DOWN:
            if current_time - self.last_scroll > SCROLL_COOLDOWN:
                self.trigger_scroll(-120)
                self.last_scroll = current_time
                target_screen_pos = (self.prev_x, self.prev_y)
                return target_screen_pos, True

        else:
            # Regular cursor movement (apply brief 60ms click-lock stabilization if just clicked/released)
            if (current_time - self.last_click_event_time) < 0.06:
                target_screen_pos = (self.prev_x, self.prev_y)
                self.prev_hand_x = filtered_cam_x
                self.prev_hand_y = filtered_cam_y
            else:
                target_screen_pos = self._update_position(filtered_cam_x, filtered_cam_y)

        return target_screen_pos, False


