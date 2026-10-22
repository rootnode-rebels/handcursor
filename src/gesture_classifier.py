"""
Gesture Classifier module for interpreting hand landmark configurations
into mouse commands (Move, Left Click, Right Click, Scroll, Idle).
Supports both Dual-Hand mode (Right moves, Left clicks) and Single-Hand mode.
"""
from enum import Enum, auto
import math
from typing import Dict, List, Optional, Tuple
from src.config import (
    PINCH_THRESHOLD_CLICK,
    PINCH_THRESHOLD_RIGHT,
    PINCH_THRESHOLD_RELEASE,
    SCROLL_THRESHOLD,
    PRIMARY_CURSOR_HAND,
    PRIMARY_ACTION_HAND
)
from src.hand_detector import HandDetector


class GestureAction(Enum):
    IDLE = auto()
    MOVE = auto()
    LEFT_CLICK = auto()
    RIGHT_CLICK = auto()
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()
    DRAG_START = auto()
    DRAG_END = auto()


class GestureClassifier:
    """Classifies hand poses into mouse interaction states."""

    def __init__(self):
        self.last_scroll_y: Optional[int] = None
        self.is_left_pinched: bool = False
        self.is_right_pinched: bool = False
        self.pinch_anchor: Optional[Tuple[int, int]] = None
        self.pinch_knuckle: Optional[Tuple[int, int]] = None
        self.dual_anchor: Optional[Tuple[int, int]] = None
        self.dual_knuckle: Optional[Tuple[int, int]] = None

    def classify_hands(
        self,
        hands: List[Dict],
        detector: HandDetector
    ) -> Tuple[Optional[Tuple[int, int]], GestureAction, Dict]:
        """
        Classifies gestures from detected hands.

        Returns:
            cursor_pos: (x, y) coordinates of pointing finger or None
            action: GestureAction enum
            debug_info: Dictionary containing active mode, distances, and details for HUD
        """
        if not hands:
            self.last_scroll_y = None
            self.is_left_pinched = False
            self.is_right_pinched = False
            self.pinch_anchor = None
            self.pinch_knuckle = None
            self.dual_anchor = None
            self.dual_knuckle = None
            return None, GestureAction.IDLE, {"mode": "No Hands Detected"}

        # ---------------------------------------------------------------------
        # DUAL-HAND MODE
        # ---------------------------------------------------------------------
        if len(hands) >= 2:
            # Sort hands horizontally by x coordinate of wrist (landmark 0)
            # In mirrored view: left side of screen is left hand, right side is right hand
            sorted_hands = sorted(hands, key=lambda h: h["landmarks"][0][0])
            left_side_hand = sorted_hands[0]
            right_side_hand = sorted_hands[1]

            # Right hand controls cursor movement
            cursor_hand = right_side_hand
            # Left hand controls actions/clicks
            action_hand = left_side_hand

            cursor_lms = cursor_hand["landmarks"]
            action_lms = action_hand["landmarks"]

            cursor_fingers = detector.fingers_up(cursor_hand)
            action_fingers = detector.fingers_up(action_hand)

            cursor_raw = (cursor_lms[8][0], cursor_lms[8][1])
            cursor_knuckle = (cursor_lms[5][0], cursor_lms[5][1])

            # In dual hand mode, index tip (landmark 8) points cleanly.
            # Stabilize cursor position when actions are executing so sympathetic finger twitch on cursor hand never moves cursor.
            if not self.is_left_pinched and not self.is_right_pinched:
                self.dual_anchor = cursor_raw
                self.dual_knuckle = cursor_knuckle
                cursor_pos = cursor_raw
            else:
                if self.dual_anchor is not None and self.dual_knuckle is not None:
                    k_dx = cursor_knuckle[0] - self.dual_knuckle[0]
                    k_dy = cursor_knuckle[1] - self.dual_knuckle[1]
                    k_disp = math.hypot(k_dx, k_dy)
                    if k_disp < 14.0:
                        cursor_pos = self.dual_anchor
                    else:
                        cursor_pos = (int(round(self.dual_anchor[0] + k_dx)), int(round(self.dual_anchor[1] + k_dy)))
                else:
                    cursor_pos = cursor_raw

            # Calculate pinches on action hand (Left Hand)
            d_thumb_index = detector.calculate_distance(
                (action_lms[4][0], action_lms[4][1]),
                (action_lms[8][0], action_lms[8][1])
            )
            # Small finger / Pinky (landmark 20) + Thumb (landmark 4) for Right Click
            # Completely avoids confusion between index and middle fingers
            d_thumb_pinky = detector.calculate_distance(
                (action_lms[4][0], action_lms[4][1]),
                (action_lms[20][0], action_lms[20][1])
            )

            # Check action gestures on left hand with hysteresis
            action = GestureAction.MOVE

            if self.is_left_pinched:
                if d_thumb_index > PINCH_THRESHOLD_RELEASE:
                    self.is_left_pinched = False
                else:
                    action = GestureAction.LEFT_CLICK
            elif self.is_right_pinched:
                if d_thumb_pinky > PINCH_THRESHOLD_RELEASE:
                    self.is_right_pinched = False
                else:
                    action = GestureAction.RIGHT_CLICK
            else:
                if d_thumb_index < PINCH_THRESHOLD_CLICK:
                    self.is_left_pinched = True
                    action = GestureAction.LEFT_CLICK
                elif d_thumb_pinky < PINCH_THRESHOLD_RIGHT:
                    self.is_right_pinched = True
                    action = GestureAction.RIGHT_CLICK
                elif action_fingers[1] and action_fingers[2] and not action_fingers[3]:
                    # Two fingers raised on action hand -> Scroll Mode
                    curr_y = (action_lms[8][1] + action_lms[12][1]) // 2
                    if self.last_scroll_y is not None:
                        delta_y = curr_y - self.last_scroll_y
                        if delta_y < -SCROLL_THRESHOLD:
                            action = GestureAction.SCROLL_UP
                            self.last_scroll_y = curr_y
                        elif delta_y > SCROLL_THRESHOLD:
                            action = GestureAction.SCROLL_DOWN
                            self.last_scroll_y = curr_y
                    else:
                        self.last_scroll_y = curr_y
                else:
                    self.last_scroll_y = None

            debug_info = {
                "mode": "Dual-Hand (R: Move | L: Action)",
                "action": action.name,
                "cursor_pos": cursor_pos,
                "left_pinch_click": round(d_thumb_index, 1),
                "left_pinch_pinky_right": round(d_thumb_pinky, 1),
                "cursor_hand_label": cursor_hand.get("label", "Right"),
                "action_hand_label": action_hand.get("label", "Left")
            }
            return cursor_pos, action, debug_info

        # ---------------------------------------------------------------------
        # SINGLE-HAND MODE (Fallback)
        # ---------------------------------------------------------------------
        hand = hands[0]
        lms = hand["landmarks"]
        fingers = detector.fingers_up(hand)
        raw_cursor = (lms[8][0], lms[8][1])
        knuckle = (lms[5][0], lms[5][1])

        d_thumb_index = detector.calculate_distance((lms[4][0], lms[4][1]), (lms[8][0], lms[8][1]))
        d_thumb_pinky = detector.calculate_distance((lms[4][0], lms[4][1]), (lms[20][0], lms[20][1]))

        # Pre-pinch stabilization: when index finger curls inward to pinch the thumb,
        # anchor the cursor to the target position so curling motion never displaces the cursor.
        # Knuckle displacement tracks real intentional whole-hand movement (e.g. dragging).
        is_closing_pinch = (d_thumb_index <= 68.0 or d_thumb_pinky <= 68.0 or self.is_left_pinched or self.is_right_pinched)

        if not is_closing_pinch or self.pinch_anchor is None or self.pinch_knuckle is None:
            self.pinch_anchor = raw_cursor
            self.pinch_knuckle = knuckle
            cursor_pos = raw_cursor
        else:
            k_dx = knuckle[0] - self.pinch_knuckle[0]
            k_dy = knuckle[1] - self.pinch_knuckle[1]
            k_disp = math.hypot(k_dx, k_dy)
            if k_disp < 14.0:
                cursor_pos = self.pinch_anchor
            else:
                cursor_pos = (int(round(self.pinch_anchor[0] + k_dx)), int(round(self.pinch_anchor[1] + k_dy)))

        action = GestureAction.IDLE

        # Single-hand pinch with hysteresis
        if self.is_left_pinched:
            if d_thumb_index > PINCH_THRESHOLD_RELEASE:
                self.is_left_pinched = False
                action = GestureAction.MOVE if fingers[1] else GestureAction.IDLE
            else:
                action = GestureAction.LEFT_CLICK
        elif self.is_right_pinched:
            if d_thumb_pinky > PINCH_THRESHOLD_RELEASE:
                self.is_right_pinched = False
                action = GestureAction.MOVE if fingers[1] else GestureAction.IDLE
            else:
                action = GestureAction.RIGHT_CLICK
        else:
            if d_thumb_index < PINCH_THRESHOLD_CLICK:
                self.is_left_pinched = True
                action = GestureAction.LEFT_CLICK
            elif d_thumb_pinky < PINCH_THRESHOLD_RIGHT:
                self.is_right_pinched = True
                action = GestureAction.RIGHT_CLICK
            elif fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
                action = GestureAction.MOVE
                self.last_scroll_y = None
            elif fingers[1] and fingers[2] and not fingers[3]:
                curr_y = (lms[8][1] + lms[12][1]) // 2
                if self.last_scroll_y is not None:
                    delta_y = curr_y - self.last_scroll_y
                    if delta_y < -SCROLL_THRESHOLD:
                        action = GestureAction.SCROLL_UP
                        self.last_scroll_y = curr_y
                    elif delta_y > SCROLL_THRESHOLD:
                        action = GestureAction.SCROLL_DOWN
                        self.last_scroll_y = curr_y
                else:
                    self.last_scroll_y = curr_y
            else:
                self.last_scroll_y = None

        debug_info = {
            "mode": "Single-Hand (All-in-One)",
            "action": action.name,
            "cursor_pos": cursor_pos,
            "pinch_click": round(d_thumb_index, 1),
            "pinch_pinky_right": round(d_thumb_pinky, 1),
            "hand_label": hand.get("label", "Unknown")
        }
        return cursor_pos, action, debug_info
