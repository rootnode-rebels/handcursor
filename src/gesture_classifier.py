"""
Gesture Classifier module for interpreting hand landmark configurations
into mouse commands (Move, Left Click, Right Click, Scroll, Idle).
Supports both Dual-Hand mode (Right moves, Left clicks) and Single-Hand mode.
"""
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple
from src.config import (
    PINCH_THRESHOLD_CLICK,
    PINCH_THRESHOLD_RIGHT,
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

            # Cursor position is index fingertip (landmark 8)
            cursor_pos = (cursor_lms[8][0], cursor_lms[8][1])

            # Calculate pinches on action hand (Left Hand)
            d_thumb_index = detector.calculate_distance(
                (action_lms[4][0], action_lms[4][1]),
                (action_lms[8][0], action_lms[8][1])
            )
            d_thumb_middle = detector.calculate_distance(
                (action_lms[4][0], action_lms[4][1]),
                (action_lms[12][0], action_lms[12][1])
            )

            # Check action gestures on left hand
            action = GestureAction.MOVE

            if d_thumb_index < PINCH_THRESHOLD_CLICK:
                action = GestureAction.LEFT_CLICK
            elif d_thumb_middle < PINCH_THRESHOLD_RIGHT:
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
                "left_pinch_right": round(d_thumb_middle, 1),
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
        cursor_pos = (lms[8][0], lms[8][1])

        d_thumb_index = detector.calculate_distance((lms[4][0], lms[4][1]), (lms[8][0], lms[8][1]))
        d_thumb_middle = detector.calculate_distance((lms[4][0], lms[4][1]), (lms[12][0], lms[12][1]))

        action = GestureAction.IDLE

        # Only Index finger up -> Move
        if fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
            action = GestureAction.MOVE
            self.last_scroll_y = None

        # Index + Thumb pinch -> Left Click
        if d_thumb_index < PINCH_THRESHOLD_CLICK:
            action = GestureAction.LEFT_CLICK

        # Middle + Thumb pinch -> Right Click
        elif d_thumb_middle < PINCH_THRESHOLD_RIGHT:
            action = GestureAction.RIGHT_CLICK

        # Index and Middle up together -> Scroll
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
            "pinch_right": round(d_thumb_middle, 1),
            "hand_label": hand.get("label", "Unknown")
        }
        return cursor_pos, action, debug_info
