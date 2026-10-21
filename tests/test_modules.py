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

    @classmethod
    def setUpClass(cls):
        cls.detector = HandDetector(max_hands=2)

    @classmethod
    def tearDownClass(cls):
        cls.detector.close()

    def setUp(self):
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

        # Converge towards screen origin (0, 0) - reaches exact minimum boundary
        for _ in range(30):
            sx_min, sy_min = self.mouse.map_coordinates(0, 0)
        self.assertEqual(sx_min, self.mouse.screen_x)
        self.assertEqual(sy_min, self.mouse.screen_y)

        # Converge to max boundaries - reaches exact maximum boundary
        for _ in range(30):
            sx_max, sy_max = self.mouse.map_coordinates(FRAME_WIDTH, FRAME_HEIGHT)
        self.assertEqual(sx_max, self.mouse.screen_x + self.mouse.screen_width - 1)
        self.assertEqual(sy_max, self.mouse.screen_y + self.mouse.screen_height - 1)

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

    def test_dual_hand_scroll(self):
        """Verify 2 fingers up and moving vertically triggers scroll."""
        right_hand = {
            "label": "Right",
            "landmarks": [(450, 400, 0)] + [(450, 300 - i*20, 0) for i in range(20)]
        }
        # Left hand with index (8) and middle (12) extended
        left_lms = [(150, 400, 0)] + [(150, 300 - i*20, 0) for i in range(20)]
        left_lms[4] = (200, 350, 0)  # Thumb folded
        left_lms[8] = (140, 120, 0)  # Index tip up
        left_lms[6] = (140, 200, 0)  # Index PIP
        left_lms[12] = (160, 120, 0) # Middle tip up
        left_lms[10] = (160, 200, 0) # Middle PIP
        left_lms[16] = (180, 280, 0) # Ring tip down
        left_lms[14] = (180, 250, 0) # Ring PIP
        left_lms[20] = (200, 280, 0) # Pinky tip down
        left_lms[18] = (200, 250, 0) # Pinky PIP

        left_hand = {"label": "Left", "landmarks": left_lms}

        # First frame registers initial scroll Y
        self.classifier.classify_hands([left_hand, right_hand], self.detector)

        # Move fingers down by 40 pixels -> SCROLL_DOWN
        left_lms_down = list(left_lms)
        left_lms_down[8] = (140, 165, 0)
        left_lms_down[12] = (160, 165, 0)
        _, action_down, _ = self.classifier.classify_hands(
            [{"label": "Left", "landmarks": left_lms_down}, right_hand],
            self.detector
        )
        self.assertEqual(action_down, GestureAction.SCROLL_DOWN)

    def test_mouse_actions_execution(self):
        """Verify MouseController executes left click, right click, and scroll without crash."""
        pos, clicked = self.mouse.execute_action((300, 300), GestureAction.LEFT_CLICK)
        self.assertTrue(self.mouse.is_left_clicked)

        # Advance timer past cooldown and test right click
        self.mouse.last_right_click = 0
        self.mouse.last_click_event_time = 0
        pos, r_clicked = self.mouse.execute_action((300, 300), GestureAction.RIGHT_CLICK)
        self.assertTrue(self.mouse.is_right_clicked)


        # Test scroll
        self.mouse.last_scroll = 0
        pos, scrolled = self.mouse.execute_action((300, 300), GestureAction.SCROLL_UP)
        self.assertTrue(scrolled)

    def test_relative_tracking_zero_jump(self):
        """Verify that showing hand in relative mode anchors without jumping cursor."""
        self.mouse.control_mode = "relative"
        self.mouse.prev_hand_x = None
        self.mouse.prev_hand_y = None

        orig_x, orig_y = self.mouse.get_cursor_pos()
        self.mouse.prev_x = orig_x
        self.mouse.prev_y = orig_y

        t0 = 1000.0
        # When hand first appears at (400, 300), cursor stays at original position
        target_pos, _ = self.mouse.execute_action((400, 300), GestureAction.MOVE, timestamp=t0)
        self.assertEqual(target_pos[0], orig_x)
        self.assertEqual(target_pos[1], orig_y)

        # When hand moves +20px right at 30fps (t = t0 + 0.033), cursor moves right relative to original position
        target_pos2, _ = self.mouse.execute_action((420, 300), GestureAction.MOVE, timestamp=t0 + 0.033)
        self.assertGreater(target_pos2[0], orig_x)



if __name__ == "__main__":
    unittest.main()
