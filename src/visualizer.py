"""
Visualizer module for rendering real-time HUD, hand skeletons,
active tracking boundaries, and gesture status feedback.
"""
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

# Provide lightweight stubs for matplotlib if missing (MediaPipe drawing_utils imports it unconditionally)
import sys
import types
if "matplotlib" not in sys.modules:
    try:
        import matplotlib
        import matplotlib.pyplot
    except ImportError:
        class _PyplotStub(types.ModuleType):
            def __getattr__(self, name): return lambda *a, **kw: None
        _mat = types.ModuleType("matplotlib")
        _mat.__path__ = []
        _plt = _PyplotStub("matplotlib.pyplot")
        sys.modules["matplotlib"] = _mat
        sys.modules["matplotlib.pyplot"] = _plt


from mediapipe.tasks.python.vision import HandLandmarksConnections


from src.config import (
    FRAME_WIDTH,
    FRAME_HEIGHT,
    MARGIN_X,
    MARGIN_Y,
    COLOR_BOUNDING_BOX,
    COLOR_RIGHT_HAND,
    COLOR_LEFT_HAND,
    COLOR_LANDMARK,
    COLOR_CONNECTION,
    COLOR_CLICK_ACTIVE
)
from src.gesture_classifier import GestureAction


class Visualizer:
    """Renders visual feedback directly onto OpenCV display frames."""

    def __init__(self):
        # Cache connection indices
        self.connections = [
            (c.start, c.end) for c in HandLandmarksConnections.HAND_CONNECTIONS
        ]
        self.margin_x = MARGIN_X
        self.margin_y = MARGIN_Y

    def draw_hud(
        self,
        frame: np.ndarray,
        hands: List[Dict],
        cursor_pos: Optional[Tuple[int, int]],
        action: GestureAction,
        fps: float,
        is_left_click: bool,
        is_right_click: bool,
        debug_info: Dict
    ) -> np.ndarray:
        """Draws complete UI overlay on the frame."""
        h, w, _ = frame.shape

        # 1. Draw Active Interaction Bounding Box (Golden Zone)
        cv2.rectangle(
            frame,
            (self.margin_x, self.margin_y),
            (w - self.margin_x, h - self.margin_y),
            COLOR_BOUNDING_BOX,
            2
        )
        cv2.putText(
            frame,
            "ACTIVE TRACKING AREA",
            (self.margin_x + 5, max(15, self.margin_y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            COLOR_BOUNDING_BOX,
            1,
            cv2.LINE_AA
        )

        # 2. Draw Hand Skeletons & Labels
        for hand in hands:
            lms = hand["landmarks"]
            # Color coding: right hand vs left hand
            is_right = (hand.get("label") == "Right" or hand.get("landmarks")[0][0] > w // 2)
            theme_color = COLOR_RIGHT_HAND if is_right else COLOR_LEFT_HAND
            role_label = "CURSOR HAND (R)" if is_right else "ACTION HAND (L)"

            # Draw bones
            for start_idx, end_idx in self.connections:
                pt1 = (lms[start_idx][0], lms[start_idx][1])
                pt2 = (lms[end_idx][0], end_idx_y := lms[end_idx][1])
                cv2.line(frame, pt1, pt2, COLOR_CONNECTION, 1, cv2.LINE_AA)

            # Draw landmark nodes
            for idx, lm in enumerate(lms):
                pt = (lm[0], lm[1])
                # Fingertips (4, 8, 12, 16, 20)
                if idx in [4, 8, 12, 16, 20]:
                    cv2.circle(frame, pt, 6, theme_color, cv2.FILLED)
                    cv2.circle(frame, pt, 8, (255, 255, 255), 1)
                else:
                    cv2.circle(frame, pt, 3, COLOR_LANDMARK, cv2.FILLED)

            # Hand role label near wrist
            wrist = (lms[0][0], max(30, lms[0][1] + 25))
            cv2.putText(
                frame,
                role_label,
                wrist,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                theme_color,
                2,
                cv2.LINE_AA
            )

        # 3. Draw Reticle on Cursor Finger (Index Tip)
        if cursor_pos is not None:
            cx, cy = cursor_pos
            reticle_color = COLOR_CLICK_ACTIVE if (is_left_click or is_right_click) else (0, 255, 0)
            cv2.circle(frame, (cx, cy), 14, reticle_color, 2, cv2.LINE_AA)
            cv2.line(frame, (cx - 20, cy), (cx + 20, cy), reticle_color, 1)
            cv2.line(frame, (cx, cy - 20), (cx, cy + 20), reticle_color, 1)

        # 4. Top Status Header (Dashboard Bar)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 55), (20, 20, 20), cv2.FILLED)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Mode & Action text
        mode_str = debug_info.get("mode", "Tracking")
        action_str = f"ACTION: {action.name}"
        if is_left_click:
            action_str = ">>> LEFT CLICK! <<<"
        elif is_right_click:
            action_str = ">>> RIGHT CLICK! <<<"

        action_color = (0, 255, 255)
        if is_left_click or is_right_click:
            action_color = (0, 0, 255)

        cv2.putText(
            frame,
            f"MODE: {mode_str}",
            (15, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )
        cv2.putText(
            frame,
            action_str,
            (15, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            action_color,
            2,
            cv2.LINE_AA
        )

        # FPS & Quit hint on top-right
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(
            frame,
            fps_text,
            (w - 110, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )
        cv2.putText(
            frame,
            "Press 'q' to Exit",
            (w - 130, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )

        return frame
