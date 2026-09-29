"""
Unit and integration tests for AI Virtual Hand Cursor modules.
"""
import unittest
import numpy as np
from src.gesture_classifier import GestureClassifier, GestureAction
from src.mouse_controller import MouseController
from src.visualizer import Visualizer
from src.hand_detector import HandDetector
from src.config import FRAME_WIDTH, FRAME_HEIGHT, MARGIN_X, MARGIN_Y


class TestVirtualCursor(unittest.TestCase):

    def setUp(self):
        self.detector = HandDetector(max_hands=2)
        self.classifier = GestureClassifier()
        self.mouse = MouseController()
        self.visualizer = Visualizer()

    def test_hand_detector_blank_frame(self):
        """Verify detector runs without error on blank frame."""
        blank_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        hands = self.detector.find_hands(blank_frame)
        self.assertIsInstance(hands, list)
        self.assertEqual(len(hands), 0)

    def test_mouse_coordinate_mapping(self):
        """Verify camera to screen coordinate interpolation and bounding box logic."""
        # Test margin center
        cx = (MARGIN_X + (FRAME_WIDTH - MARGIN_X)) // 2
        cy = (MARGIN_Y + (FRAME_HEIGHT - MARGIN_Y)) // 2
        sx, sy = self.mouse.map_coordinates(cx, cy)
        
        # Center should be roughly half screen width/height
        self.assertAlmostEqual(sx, self.mouse.screen_width // 2, delta=20)
        self.assertAlmostEqual(sy, self.mouse.screen_height // 2, delta=20)

        # Converge towards (0, 0) over several iterations; stops within deadzone radius
        for _ in range(30):
            sx_min, sy_min = self.mouse.map_coordinates(0, 0)
        self.assertLessEqual(sx_min, 8)
        self.assertLessEqual(sy_min, 8)

        # Converge to max boundaries
        for _ in range(30):
            sx_max, sy_max = self.mouse.map_coordinates(FRAME_WIDTH, FRAME_HEIGHT)
        self.assertLessEqual(sx_max, self.mouse.screen_width - 1)
        self.assertLessEqual(sy_max, self.mouse.screen_height - 1)

    def test_gesture_classifier_no_hands(self):
        """Verify classifier outputs IDLE when no hands detected."""
        cursor_pos, action, debug_info = self.classifier.classify_hands([], self.detector)
        self.assertIsNone(cursor_pos)
        self.assertEqual(action, GestureAction.IDLE)

    def test_visualizer_renders_without_crash(self):
        """Verify HUD rendering operates on frame."""
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        rendered = self.visualizer.draw_hud(
            frame=frame,
            hands=[],
            cursor_pos=(200, 200),
            action=GestureAction.MOVE,
            fps=30.0,
            is_left_click=False,
            is_right_click=False,
            debug_info={"mode": "Test Mode"}
        )
        self.assertEqual(rendered.shape, (FRAME_HEIGHT, FRAME_WIDTH, 3))

    def test_dual_hand_left_click(self):
        """Verify left hand pinch triggers LEFT_CLICK in dual hand mode."""
        # Simulated right hand (wrist at x=450, index tip at x=450, y=200)
        right_hand = {
            "label": "Right",
            "landmarks": [(450, 400, 0)] + [(450, 300 - i*20, 0) for i in range(20)]
        }
        # Simulated left hand (wrist at x=150)
        # Thumb tip (4) and Index tip (8) very close (< 20px) -> pinch!
        left_lms = [(150, 400, 0)] + [(150, 300 - i*20, 0) for i in range(20)]
        left_lms[4] = (150, 200, 0)   # Thumb tip
        left_lms[8] = (155, 205, 0)   # Index tip (dist ~7px)
        left_lms[12] = (150, 150, 0)  # Middle tip far away
        left_hand = {
            "label": "Left",
            "landmarks": left_lms
        }

        cursor_pos, action, debug_info = self.classifier.classify_hands(
            [left_hand, right_hand],
            self.detector
        )
        self.assertEqual(action, GestureAction.LEFT_CLICK)
        self.assertEqual(cursor_pos, (right_hand["landmarks"][8][0], right_hand["landmarks"][8][1]))

    def test_dual_hand_right_click(self):
        """Verify left hand thumb+middle pinch triggers RIGHT_CLICK in dual hand mode."""
        right_hand = {
            "label": "Right",
            "landmarks": [(450, 400, 0)] + [(450, 300 - i*20, 0) for i in range(20)]
        }
        left_lms = [(150, 400, 0)] + [(150, 300 - i*20, 0) for i in range(20)]
        left_lms[4] = (150, 200, 0)   # Thumb tip
        left_lms[8] = (150, 100, 0)   # Index tip far away
        left_lms[12] = (155, 205, 0)  # Middle tip close (< 10px) -> right click!
        left_hand = {
            "label": "Left",
            "landmarks": left_lms
        }

        cursor_pos, action, debug_info = self.classifier.classify_hands(
            [left_hand, right_hand],
            self.detector
        )
        self.assertEqual(action, GestureAction.RIGHT_CLICK)

    def tearDown(self):
        self.detector.close()


if __name__ == "__main__":
    unittest.main()
