"""
AI Virtual Hand Cursor - Professional Desktop Python Application.
Featuring:
- Modern Glassmorphism/Dark UI with real-time gesture feedback
- Hand Tracking status chips (Right Hand & Left Hand detection indicators)
- Live Tuning Sliders (Smoothing, Click-Lock Freeze, Tremor Deadzone)
- Always-On-Top floating HUD mode with draggable support
- Native Win32 API cursor engine with 0ms latency
- Keyboard Shortcuts: Space (Pause/Resume), P (Pin/Float), C (Camera On/Off)
"""
import sys
import time
import cv2
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QImage, QPixmap, QColor, QFont, QIcon

from src.config import (
    CAMERA_ID,
    CAMERA_BACKEND,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    MARGIN_X,
    MARGIN_Y,
    SMOOTHING_FACTOR,
    DEADZONE_RADIUS,
    CLICK_FREEZE_TIME,
    CONTROL_MODE,
    MOUSE_SENSITIVITY
)
from src.hand_detector import HandDetector
from src.gesture_classifier import GestureAction, GestureClassifier
from src.mouse_controller import MouseController
from src.visualizer import Visualizer


class DesktopTrackingWorker(QThread):
    """Background worker thread running computer vision and mouse tracking."""
    frame_ready = pyqtSignal(QImage, dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.mouse_enabled = True
        self.show_skeleton = True
        self.cap = None

        # Controller instances
        self.mouse = MouseController()
        self.visualizer = Visualizer()

    def start_camera(self):
        """Starts webcam on user command."""
        if not self.isRunning():
            self.running = True
            self.start()

    def stop_camera(self):
        """Releases camera hardware immediately."""
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.wait()

    def update_settings(
        self,
        smoothing: int,
        deadzone: int,
        click_freeze: float,
        show_skeleton: bool,
        margin: int = MARGIN_X,
        control_mode: str = CONTROL_MODE,
        sensitivity: float = MOUSE_SENSITIVITY
    ):
        """Updates tracking parameters in real time."""
        self.mouse.smoothing_factor = smoothing
        self.mouse.deadzone_radius = deadzone
        self.mouse.click_freeze_time = click_freeze
        self.mouse.margin_x = margin
        self.mouse.margin_y = max(10, int(margin * 0.8))
        self.mouse.control_mode = control_mode
        self.mouse.sensitivity = sensitivity
        self.mouse.update_screen_metrics()
        self.visualizer.margin_x = margin
        self.visualizer.margin_y = max(10, int(margin * 0.8))
        self.visualizer.control_mode = control_mode
        self.show_skeleton = show_skeleton

    def run(self):
        print(f"[DESKTOP APP] Opening camera {CAMERA_ID} with DirectShow backend...")
        self.cap = cv2.VideoCapture(CAMERA_ID, CAMERA_BACKEND)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        if not self.cap.isOpened():
            self.error_occurred.emit("Webcam not found or inaccessible.")
            self.running = False
            return

        detector = HandDetector(max_hands=2)
        classifier = GestureClassifier()
        visualizer = self.visualizer

        prev_time = time.time()
        fps = 0.0

        try:
            while self.running:
                if self.cap is None or not self.cap.isOpened():
                    break

                success, frame = self.cap.read()
                if not success or frame is None:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)

                curr_time = time.time()
                dt = curr_time - prev_time
                if dt > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps > 0 else (1.0 / dt)
                prev_time = curr_time

                # Hand Detection & Gestures
                hands = detector.find_hands(frame)
                cursor_pos, action, debug_info = classifier.classify_hands(hands, detector)

                # Mouse Actions (Across entire desktop)
                if self.mouse_enabled:
                    self.mouse.execute_action(cursor_pos, action)
                else:
                    self.mouse.is_left_clicked = False
                    self.mouse.is_right_clicked = False

                # Visual HUD
                if self.show_skeleton:
                    frame = visualizer.draw_hud(
                        frame=frame,
                        hands=hands,
                        cursor_pos=cursor_pos,
                        action=action,
                        fps=fps,
                        is_left_click=self.mouse.is_left_clicked,
                        is_right_click=self.mouse.is_right_clicked,
                        debug_info=debug_info
                    )

                # Check which hands are currently in view
                right_hand_found = False
                left_hand_found = False
                for h in hands:
                    wrist_x = h["landmarks"][0][0]
                    if wrist_x > FRAME_WIDTH // 2:
                        right_hand_found = True
                    else:
                        left_hand_found = True

                # Convert to QImage
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

                status_data = {
                    "fps": round(fps, 1),
                    "action": action.name,
                    "mode": debug_info.get("mode", "Tracking"),
                    "is_left_click": self.mouse.is_left_clicked,
                    "is_right_click": self.mouse.is_right_clicked,
                    "hands_count": len(hands),
                    "right_hand": right_hand_found,
                    "left_hand": left_hand_found,
                    "mouse_enabled": self.mouse_enabled
                }

                self.frame_ready.emit(q_img, status_data)
                time.sleep(0.01)

        finally:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            detector.close()
            print("[DESKTOP APP] Camera hardware released safely.")


class DesktopAppWindow(QtWidgets.QMainWindow):
    """Modern Desktop Application Window for Virtual Hand Cursor."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Hand Cursor")
        self.resize(440, 710)
        self.setMinimumSize(380, 580)

        # Window state
        self.is_pinned = True
        self.is_compact = False
        self.camera_active = False
        self.drag_position = QPoint()

        self.update_window_flags()
        self.init_ui()

        # Initialize tracking worker (camera is OFF by default)
        self.worker = DesktopTrackingWorker()
        self.worker.frame_ready.connect(self.update_display)
        self.worker.error_occurred.connect(self.show_error)

        # Synchronize initial GUI slider settings with worker
        self.on_settings_changed()

        # Position window at bottom-right of screen
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.move(screen.width() - 470, screen.height() - 770)

    def update_window_flags(self):
        """Toggles between always-on-top floating mode and standard window."""
        flags = Qt.WindowType.Window
        if self.is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def init_ui(self):
        # Central Widget & Global Styling
        central_widget = QtWidgets.QWidget(self)
        central_widget.setStyleSheet("""
            QWidget {
                background-color: #090d16;
                color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            }
            QFrame.card {
                background-color: #131b2e;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background-color: #0d1527;
                border-radius: 10px;
                padding: 6px;
            }
            QTabBar::tab {
                background: #131b2e;
                color: #94a3b8;
                padding: 8px 16px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 11px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #0284c7;
                color: #ffffff;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e293b;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0284c7;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #38bdf8;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
        """)
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        # 1. Header Toolbar
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("✋ Virtual Hand Cursor")
        title.setStyleSheet("font-size: 14px; font-weight: 800; color: #38bdf8; letter-spacing: 0.3px;")

        self.pin_btn = QtWidgets.QPushButton("📌 Pinned")
        self.pin_btn.setFixedSize(68, 26)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setStyleSheet("""
            QPushButton { background: #0284c7; color: white; border-radius: 6px; font-size: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background: #0369a1; }
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)

        self.compact_btn = QtWidgets.QPushButton("—")
        self.compact_btn.setFixedSize(26, 26)
        self.compact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compact_btn.setStyleSheet("""
            QPushButton { background: #1e293b; color: white; border-radius: 6px; font-size: 12px; font-weight: bold; border: none; }
            QPushButton:hover { background: #334155; }
        """)
        self.compact_btn.clicked.connect(self.toggle_compact)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.pin_btn)
        header.addWidget(self.compact_btn)
        layout.addLayout(header)

        # 2. Main Tabs (Live HUD vs Settings & Tuning)
        self.tabs = QtWidgets.QTabWidget()
        
        # --- TAB 1: LIVE VIEW ---
        tab_live = QtWidgets.QWidget()
        live_layout = QtWidgets.QVBoxLayout(tab_live)
        live_layout.setContentsMargins(4, 6, 4, 4)
        live_layout.setSpacing(8)

        # Camera Preview Box
        self.video_box = QtWidgets.QLabel()
        self.video_box.setFixedHeight(270)
        self.video_box.setStyleSheet("background-color: #020617; border-radius: 10px; border: 1px solid #1e293b; color: #64748b; font-size: 12px;")
        self.video_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_box.setText("Camera is currently OFF\nClick 'Enable Camera' below to start")
        live_layout.addWidget(self.video_box)

        # Hand Detection Status Badges
        hand_status_layout = QtWidgets.QHBoxLayout()
        self.badge_right = QtWidgets.QLabel("● Right (Cursor): Inactive")
        self.badge_right.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;")
        self.badge_left = QtWidgets.QLabel("● Left (Action): Inactive")
        self.badge_left.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;")
        hand_status_layout.addWidget(self.badge_right)
        hand_status_layout.addWidget(self.badge_left)
        live_layout.addLayout(hand_status_layout)

        # Real-time Action Banner
        self.action_card = QtWidgets.QFrame()
        self.action_card.setProperty("class", "card")
        self.action_card.setStyleSheet("background-color: #131b2e; border: 1px solid #1e293b; border-radius: 10px; padding: 4px;")
        action_layout = QtWidgets.QHBoxLayout(self.action_card)
        action_layout.setContentsMargins(10, 6, 10, 6)

        self.action_label = QtWidgets.QLabel("ACTION: IDLE")
        self.action_label.setStyleSheet("font-weight: 800; font-size: 12px; color: #38bdf8;")

        self.fps_label = QtWidgets.QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 11px;")
        self.fps_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        action_layout.addWidget(self.action_label)
        action_layout.addWidget(self.fps_label)
        live_layout.addWidget(self.action_card)

        # Camera Master Control Button
        self.btn_camera = QtWidgets.QPushButton("🎥 Enable Camera")
        self.btn_camera.setFixedHeight(36)
        self.btn_camera.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_camera.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: 700;
                font-size: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_camera.clicked.connect(self.toggle_camera)
        live_layout.addWidget(self.btn_camera)

        # Mouse Tracking Pause/Resume Button
        self.btn_mouse = QtWidgets.QPushButton("● Mouse Movement: ACTIVE (Space to Pause)")
        self.btn_mouse.setFixedHeight(32)
        self.btn_mouse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mouse.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                font-weight: 700;
                font-size: 11px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #22c55e; }
        """)
        self.btn_mouse.clicked.connect(self.toggle_mouse)
        live_layout.addWidget(self.btn_mouse)

        # Gestures Quick Reference Card
        guide_card = QtWidgets.QFrame()
        guide_card.setProperty("class", "card")
        guide_layout = QtWidgets.QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(10, 8, 10, 8)
        guide_layout.setSpacing(3)

        guide_title = QtWidgets.QLabel("Quick Controls:")
        guide_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; text-transform: uppercase;")
        guide_layout.addWidget(guide_title)

        r_move = QtWidgets.QLabel("• <b>Right Hand Index</b>: Point & move cursor smoothly")
        r_move.setStyleSheet("font-size: 11px; color: #4ade80;")
        guide_layout.addWidget(r_move)

        l_click = QtWidgets.QLabel("• <b>Left Thumb + Index</b>: Left Click (Locks position)")
        l_click.setStyleSheet("font-size: 11px; color: #f472b6;")
        guide_layout.addWidget(l_click)

        l_rclick = QtWidgets.QLabel("• <b>Left Thumb + Pinky (Small Finger)</b>: Right Click")
        l_rclick.setStyleSheet("font-size: 11px; color: #c084fc;")
        guide_layout.addWidget(l_rclick)

        l_scroll = QtWidgets.QLabel("• <b>Left Index + Middle</b>: Scroll Up / Down")
        l_scroll.setStyleSheet("font-size: 11px; color: #f59e0b;")
        guide_layout.addWidget(l_scroll)

        live_layout.addWidget(guide_card)
        self.tabs.addTab(tab_live, "Live Tracker")

        # --- TAB 2: TUNING & SETTINGS ---
        tab_settings = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(tab_settings)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(12)

        # 0. Navigation Control Mode Selector
        lbl_mode_title = QtWidgets.QLabel("Cursor Control Mode:")
        lbl_mode_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8;")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItem("Air Mouse (Relative) - Zero Jumps, Full Screen Reach", "relative")
        self.combo_mode.addItem("Absolute (Screen Mapping) - Direct Camera-to-Screen Mapping", "absolute")
        self.combo_mode.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #0284c7;
            }
        """)
        self.combo_mode.currentIndexChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(lbl_mode_title)
        settings_layout.addWidget(self.combo_mode)

        # 1. Mouse Sensitivity / Speed (Air Mouse Mode)
        self.lbl_sens = QtWidgets.QLabel(f"Air Mouse Sensitivity: {MOUSE_SENSITIVITY}x (Full Screen Reach)")
        self.lbl_sens.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.slider_sens = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(10, 60)
        self.slider_sens.setValue(int(MOUSE_SENSITIVITY * 10))
        self.slider_sens.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.lbl_sens)
        settings_layout.addWidget(self.slider_sens)

        # 2. Smoothing Slider
        self.lbl_smooth = QtWidgets.QLabel(f"Cursor Smoothing: {SMOOTHING_FACTOR} (Balanced)")
        self.lbl_smooth.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.slider_smooth = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth.setRange(1, 10)
        self.slider_smooth.setValue(SMOOTHING_FACTOR)
        self.slider_smooth.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.lbl_smooth)
        settings_layout.addWidget(self.slider_smooth)

        # 3. Deadzone Filter Slider
        self.lbl_deadzone = QtWidgets.QLabel(f"Tremor Deadzone: {DEADZONE_RADIUS}px")
        self.lbl_deadzone.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.slider_deadzone = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_deadzone.setRange(2, 20)
        self.slider_deadzone.setValue(DEADZONE_RADIUS)
        self.slider_deadzone.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.lbl_deadzone)
        settings_layout.addWidget(self.slider_deadzone)

        # 4. Click Freeze Duration Slider
        self.lbl_freeze = QtWidgets.QLabel(f"Click-Lock Freeze: {CLICK_FREEZE_TIME}s")
        self.lbl_freeze.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.slider_freeze = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_freeze.setRange(10, 80)
        self.slider_freeze.setValue(int(CLICK_FREEZE_TIME * 100))
        self.slider_freeze.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.lbl_freeze)
        settings_layout.addWidget(self.slider_freeze)

        # 5. Active Control Frame Size Slider (smaller margin = larger control area)
        self.lbl_margin = QtWidgets.QLabel(f"Active Frame Size: {FRAME_WIDTH - 2*MARGIN_X}×{FRAME_HEIGHT - 2*MARGIN_Y} px (Margin: {MARGIN_X}px)")
        self.lbl_margin.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.slider_margin = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_margin.setRange(10, 90)
        self.slider_margin.setValue(MARGIN_X)
        self.slider_margin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.lbl_margin)
        settings_layout.addWidget(self.slider_margin)

        # 6. Show Skeleton Toggle
        self.chk_skeleton = QtWidgets.QCheckBox("Render Hand Skeletons & Boundaries")
        self.chk_skeleton.setChecked(True)
        self.chk_skeleton.setStyleSheet("font-size: 11px; color: #cbd5e1; font-weight: 600;")
        self.chk_skeleton.stateChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.chk_skeleton)

        # Keyboard shortcuts reference
        shortcuts_box = QtWidgets.QFrame()
        shortcuts_box.setStyleSheet("background-color: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        sc_layout = QtWidgets.QVBoxLayout(shortcuts_box)
        sc_layout.setSpacing(2)
        sc_title = QtWidgets.QLabel("Keyboard Shortcuts:")
        sc_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8;")
        sc1 = QtWidgets.QLabel("• <b>[Space]</b> : Pause or Resume Mouse Movement")
        sc1.setStyleSheet("font-size: 10px; color: #94a3b8;")
        sc2 = QtWidgets.QLabel("• <b>[P]</b> : Toggle Pin Always-On-Top")
        sc2.setStyleSheet("font-size: 10px; color: #94a3b8;")
        sc_layout.addWidget(sc_title)
        sc_layout.addWidget(sc1)
        sc_layout.addWidget(sc2)
        settings_layout.addWidget(shortcuts_box)

        settings_layout.addStretch()
        self.tabs.addTab(tab_settings, "Tuning & Preferences")

        layout.addWidget(self.tabs)

    def on_settings_changed(self):
        """Dispatches live slider adjustments directly to worker."""
        mode = self.combo_mode.currentData() or "relative"
        sens = self.slider_sens.value() / 10.0
        smooth = self.slider_smooth.value()
        deadzone = self.slider_deadzone.value()
        freeze = self.slider_freeze.value() / 100.0
        margin = self.slider_margin.value()
        show_skel = self.chk_skeleton.isChecked()

        margin_y = max(10, int(margin * 0.8))
        active_w = FRAME_WIDTH - 2 * margin
        active_h = FRAME_HEIGHT - 2 * margin_y

        # Update labels
        self.lbl_sens.setText(f"Air Mouse Sensitivity: {sens:.1f}x ({'Slow' if sens < 1.6 else 'Fast' if sens > 2.8 else 'Balanced'})")
        self.lbl_smooth.setText(f"Cursor Smoothing: {smooth} ({'Fast' if smooth < 3 else 'Smooth' if smooth > 5 else 'Balanced'})")
        self.lbl_deadzone.setText(f"Tremor Deadzone: {deadzone}px")
        self.lbl_freeze.setText(f"Click-Lock Freeze: {freeze:.2f}s")
        self.lbl_margin.setText(f"Active Frame Size: {active_w}×{active_h} px (Margin: {margin}px)")

        self.worker.update_settings(
            smooth,
            deadzone,
            freeze,
            show_skel,
            margin=margin,
            control_mode=mode,
            sensitivity=sens
        )

    def toggle_pin(self):
        """Toggles always-on-top window property."""
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.pin_btn.setText("📌 Pinned")
            self.pin_btn.setStyleSheet("background: #0284c7; color: white; border-radius: 6px; font-size: 10px; font-weight: bold; border: none;")
        else:
            self.pin_btn.setText("Unpinned")
            self.pin_btn.setStyleSheet("background: #334155; color: #94a3b8; border-radius: 6px; font-size: 10px; font-weight: bold; border: none;")

        self.update_window_flags()
        self.show()

    def toggle_compact(self):
        """Toggles compact minimal view."""
        self.is_compact = not self.is_compact
        if self.is_compact:
            self.tabs.hide()
            self.compact_btn.setText("□")
            self.resize(340, 60)
        else:
            self.tabs.show()
            self.compact_btn.setText("—")
            self.resize(440, 710)

    def toggle_camera(self):
        """Starts or stops webcam on user explicit request."""
        self.camera_active = not self.camera_active
        if self.camera_active:
            self.btn_camera.setText("⏹ Stop Camera")
            self.btn_camera.setStyleSheet("""
                QPushButton { background-color: #dc2626; color: white; font-weight: 700; font-size: 12px; border-radius: 8px; border: none; }
                QPushButton:hover { background-color: #ef4444; }
            """)
            self.video_box.setText("Starting camera...")
            self.worker.start_camera()
        else:
            self.btn_camera.setText("🎥 Enable Camera")
            self.btn_camera.setStyleSheet("""
                QPushButton { background-color: #0284c7; color: white; font-weight: 700; font-size: 12px; border-radius: 8px; border: none; }
                QPushButton:hover { background-color: #0369a1; }
            """)
            self.worker.stop_camera()
            self.video_box.clear()
            self.video_box.setText("Camera is currently OFF\nClick 'Enable Camera' above to start")
            self.fps_label.setText("FPS: --")
            self.action_label.setText("ACTION: IDLE")
            self.badge_right.setText("● Right (Cursor): Inactive")
            self.badge_right.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;")
            self.badge_left.setText("● Left (Action): Inactive")
            self.badge_left.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;")

    def toggle_mouse(self):
        """Toggles OS cursor control on or off."""
        self.worker.mouse_enabled = not self.worker.mouse_enabled
        if self.worker.mouse_enabled:
            self.btn_mouse.setText("● Mouse Movement: ACTIVE (Space to Pause)")
            self.btn_mouse.setStyleSheet("""
                QPushButton { background-color: #16a34a; color: white; font-weight: 700; font-size: 11px; border-radius: 8px; border: none; }
                QPushButton:hover { background-color: #22c55e; }
            """)
        else:
            self.btn_mouse.setText("○ Mouse Movement: PAUSED (Space to Resume)")
            self.btn_mouse.setStyleSheet("""
                QPushButton { background-color: #dc2626; color: white; font-weight: 700; font-size: 11px; border-radius: 8px; border: none; }
                QPushButton:hover { background-color: #ef4444; }
            """)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Hotkeys: Spacebar (Pause/Resume), P (Pin), C (Camera)."""
        if event.key() == Qt.Key.Key_Space:
            self.toggle_mouse()
            event.accept()
        elif event.key() == Qt.Key.Key_P:
            self.toggle_pin()
            event.accept()
        elif event.key() == Qt.Key.Key_C:
            self.toggle_camera()
            event.accept()
        else:
            super().keyPressEvent(event)

    def update_display(self, q_img: QImage, status: dict):
        if self.camera_active and not self.is_compact:
            pixmap = QPixmap.fromImage(q_img).scaled(
                self.video_box.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_box.setPixmap(pixmap)

        self.fps_label.setText(f"FPS: {status['fps']}")

        # Hand Status Badges
        if status.get("right_hand"):
            self.badge_right.setText("✓ Right Hand: Tracked")
            self.badge_right.setStyleSheet("background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;")
        else:
            self.badge_right.setText("○ Right Hand: Searching")
            self.badge_right.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;")

        if status.get("left_hand"):
            self.badge_left.setText("✓ Left Hand: Tracked")
            self.badge_left.setStyleSheet("background: rgba(244, 114, 182, 0.2); color: #f472b6; border: 1px solid #ec4899; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;")
        else:
            self.badge_left.setText("○ Left Hand: Searching")
            self.badge_left.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 600;")

        # Action Badge styling
        action_name = status['action']
        if status.get('is_left_click'):
            self.action_label.setText(">>> LEFT CLICK! <<<")
            self.action_label.setStyleSheet("color: #f43f5e; font-weight: 800; font-size: 12px;")
            self.action_card.setStyleSheet("background-color: rgba(244, 63, 94, 0.15); border: 1px solid #f43f5e; border-radius: 10px; padding: 4px;")
        elif status.get('is_right_click'):
            self.action_label.setText(">>> RIGHT CLICK! <<<")
            self.action_label.setStyleSheet("color: #c084fc; font-weight: 800; font-size: 12px;")
            self.action_card.setStyleSheet("background-color: rgba(192, 132, 252, 0.15); border: 1px solid #c084fc; border-radius: 10px; padding: 4px;")
        elif action_name == "MOVE":
            self.action_label.setText("ACTION: MOVING")
            self.action_label.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 12px;")
            self.action_card.setStyleSheet("background-color: #131b2e; border: 1px solid #0284c7; border-radius: 10px; padding: 4px;")
        elif "SCROLL" in action_name:
            self.action_label.setText(f"ACTION: {action_name}")
            self.action_label.setStyleSheet("color: #f59e0b; font-weight: 800; font-size: 12px;")
            self.action_card.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; border-radius: 10px; padding: 4px;")
        else:
            self.action_label.setText(f"ACTION: {action_name}")
            self.action_label.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
            self.action_card.setStyleSheet("background-color: #131b2e; border: 1px solid #1e293b; border-radius: 10px; padding: 4px;")

    def show_error(self, message: str):
        self.video_box.setText(f"Error: {message}")

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Ensures camera hardware is stopped when window is closed."""
        if hasattr(self, 'worker'):
            self.worker.stop_camera()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = DesktopAppWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
