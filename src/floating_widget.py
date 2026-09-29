"""
Floating Desktop Overlay Widget for AI Virtual Hand Cursor using PyQt6.
Always-on-top, draggable, collapsible floating HUD with user-controlled camera.
Works globally across the entire desktop, all browsers, and applications.
"""
import sys
import time
import cv2
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter

from src.config import CAMERA_ID, CAMERA_BACKEND, FRAME_WIDTH, FRAME_HEIGHT
from src.hand_detector import HandDetector
from src.gesture_classifier import GestureClassifier, GestureAction
from src.mouse_controller import MouseController
from src.visualizer import Visualizer


class TrackingWorker(QThread):
    """Background worker thread running computer vision and mouse tracking."""
    frame_ready = pyqtSignal(QImage, dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.mouse_enabled = True
        self.cap = None

    def start_camera(self):
        """Starts the camera upon explicit user action."""
        if not self.isRunning():
            self.running = True
            self.start()

    def stop_camera(self):
        """Immediately stops the camera and releases the hardware."""
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.wait()

    def run(self):
        print(f"[FLOATING HUD] User initiated camera start (Backend: DirectShow, Camera ID: {CAMERA_ID})...")
        self.cap = cv2.VideoCapture(CAMERA_ID, CAMERA_BACKEND)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        if not self.cap.isOpened():
            self.error_occurred.emit("Webcam not accessible.")
            self.running = False
            return

        detector = HandDetector(max_hands=2)
        classifier = GestureClassifier()
        mouse = MouseController()
        visualizer = Visualizer()

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

                # Detect Hands
                hands = detector.find_hands(frame)
                cursor_pos, action, debug_info = classifier.classify_hands(hands, detector)

                # Mouse Actions (across entire desktop)
                if self.mouse_enabled:
                    mouse.execute_action(cursor_pos, action)
                else:
                    mouse.is_left_clicked = False
                    mouse.is_right_clicked = False

                # Visual HUD
                frame = visualizer.draw_hud(
                    frame=frame,
                    hands=hands,
                    cursor_pos=cursor_pos,
                    action=action,
                    fps=fps,
                    is_left_click=mouse.is_left_clicked,
                    is_right_click=mouse.is_right_clicked,
                    debug_info=debug_info
                )

                # Convert to QImage
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

                status_data = {
                    "fps": round(fps, 1),
                    "action": action.name,
                    "mode": debug_info.get("mode", "Tracking"),
                    "is_left_click": mouse.is_left_clicked,
                    "is_right_click": mouse.is_right_clicked,
                    "hands_count": len(hands),
                    "mouse_enabled": self.mouse_enabled
                }

                self.frame_ready.emit(q_img, status_data)
                time.sleep(0.01)

        finally:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            detector.close()
            print("[FLOATING HUD] Camera hardware released safely.")


class FloatingOverlay(QtWidgets.QWidget):
    """Always-on-top, draggable, collapsible floating desktop HUD."""

    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.is_collapsed = False
        self.camera_active = False

        # Set Window Flags: Stays on Top of all windows, frameless tool widget
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.init_ui()

        # Initialize tracking worker (camera is OFF by default)
        self.worker = TrackingWorker()
        self.worker.frame_ready.connect(self.update_display)
        self.worker.error_occurred.connect(self.show_error)

        # Position widget at bottom-right of primary screen
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.move(screen.width() - 340, screen.height() - 480)

    def init_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)

        # Main container card
        self.container = QtWidgets.QFrame(self)
        self.container.setStyleSheet("""
            QFrame#container {
                background-color: rgba(15, 23, 42, 240);
                border: 1px solid #334155;
                border-radius: 14px;
            }
        """)
        self.container.setObjectName("container")

        self.container_layout = QtWidgets.QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 10, 12, 12)
        self.container_layout.setSpacing(8)

        # 1. Draggable Header Bar
        self.header_layout = QtWidgets.QHBoxLayout()

        self.title_label = QtWidgets.QLabel("✋ Virtual Cursor", self)
        self.title_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")

        self.status_pill = QtWidgets.QLabel("Camera Off", self)
        self.status_pill.setStyleSheet("color: #94a3b8; font-size: 10px; background: #1e293b; padding: 2px 6px; border-radius: 4px;")

        self.btn_collapse = QtWidgets.QPushButton("—", self)
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setStyleSheet("""
            QPushButton { background: #334155; color: white; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #475569; }
        """)
        self.btn_collapse.clicked.connect(self.toggle_collapse)

        self.btn_close = QtWidgets.QPushButton("✕", self)
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton { background: #dc2626; color: white; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #ef4444; }
        """)
        self.btn_close.clicked.connect(self.close_app)

        self.header_layout.addWidget(self.title_label)
        self.header_layout.addWidget(self.status_pill)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.btn_collapse)
        self.header_layout.addWidget(self.btn_close)

        self.container_layout.addLayout(self.header_layout)

        # 2. Body Widget
        self.body_widget = QtWidgets.QWidget(self)
        self.body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)

        # Video Preview Box
        self.video_label = QtWidgets.QLabel(self)
        self.video_label.setFixedSize(290, 218)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 8px; border: 1px solid #1e293b; color: #64748b; font-size: 12px;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("Camera is currently OFF\nClick 'Enable Camera' below")
        self.body_layout.addWidget(self.video_label)

        # Action & Mode Status Bar
        self.status_card = QtWidgets.QFrame(self)
        self.status_card.setStyleSheet("background-color: #1e293b; border-radius: 8px;")
        status_card_layout = QtWidgets.QHBoxLayout(self.status_card)
        status_card_layout.setContentsMargins(8, 6, 8, 6)

        self.action_label = QtWidgets.QLabel("ACTION: IDLE", self)
        self.action_label.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 11px;")

        self.fps_label = QtWidgets.QLabel("FPS: --", self)
        self.fps_label.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 600;")
        self.fps_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        status_card_layout.addWidget(self.action_label)
        status_card_layout.addWidget(self.fps_label)
        self.body_layout.addWidget(self.status_card)

        # Camera Start/Stop Button
        self.btn_camera = QtWidgets.QPushButton("🎥 Enable Camera", self)
        self.btn_camera.setFixedHeight(32)
        self.btn_camera.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_camera.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_camera.clicked.connect(self.toggle_camera)
        self.body_layout.addWidget(self.btn_camera)

        # Mouse Control Toggle Button
        self.btn_toggle_mouse = QtWidgets.QPushButton("● Mouse Control: ACTIVE", self)
        self.btn_toggle_mouse.setFixedHeight(30)
        self.btn_toggle_mouse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_mouse.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #22c55e; }
        """)
        self.btn_toggle_mouse.clicked.connect(self.toggle_mouse)
        self.body_layout.addWidget(self.btn_toggle_mouse)

        # Drag hint
        self.hint_label = QtWidgets.QLabel("Drag anywhere to move • Right: Move | Left: Click", self)
        self.hint_label.setStyleSheet("color: #64748b; font-size: 9px;")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_layout.addWidget(self.hint_label)

        self.container_layout.addWidget(self.body_widget)
        self.main_layout.addWidget(self.container)

    def toggle_camera(self):
        """Starts or stops the webcam upon user command."""
        self.camera_active = not self.camera_active
        if self.camera_active:
            self.status_pill.setText("Camera ON")
            self.status_pill.setStyleSheet("color: #4ade80; font-size: 10px; background: rgba(34, 197, 94, 0.2); padding: 2px 6px; border-radius: 4px; border: 1px solid #22c55e;")
            self.btn_camera.setText("⏹ Stop Camera")
            self.btn_camera.setStyleSheet("""
                QPushButton { background-color: #dc2626; color: white; font-weight: bold; font-size: 12px; border-radius: 6px; }
                QPushButton:hover { background-color: #ef4444; }
            """)
            self.video_label.setText("Starting camera...")
            self.worker.start_camera()
        else:
            self.status_pill.setText("Camera Off")
            self.status_pill.setStyleSheet("color: #94a3b8; font-size: 10px; background: #1e293b; padding: 2px 6px; border-radius: 4px;")
            self.btn_camera.setText("🎥 Enable Camera")
            self.btn_camera.setStyleSheet("""
                QPushButton { background-color: #0284c7; color: white; font-weight: bold; font-size: 12px; border-radius: 6px; }
                QPushButton:hover { background-color: #0369a1; }
            """)
            self.worker.stop_camera()
            self.video_label.clear()
            self.video_label.setText("Camera is currently OFF\nClick 'Enable Camera' below")
            self.fps_label.setText("FPS: --")
            self.action_label.setText("ACTION: IDLE")

    def toggle_collapse(self):
        """Collapses or expands widget to save desktop space."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.body_widget.hide()
            self.btn_collapse.setText("+")
            self.resize(200, 50)
        else:
            self.body_widget.show()
            self.btn_collapse.setText("—")
            self.resize(320, 390)

    def toggle_mouse(self):
        """Toggles physical mouse movement on or off."""
        self.worker.mouse_enabled = not self.worker.mouse_enabled
        if self.worker.mouse_enabled:
            self.btn_toggle_mouse.setText("● Mouse Control: ACTIVE")
            self.btn_toggle_mouse.setStyleSheet("""
                QPushButton { background-color: #16a34a; color: white; font-weight: bold; font-size: 11px; border-radius: 6px; }
                QPushButton:hover { background-color: #22c55e; }
            """)
        else:
            self.btn_toggle_mouse.setText("○ Mouse Control: PAUSED")
            self.btn_toggle_mouse.setStyleSheet("""
                QPushButton { background-color: #dc2626; color: white; font-weight: bold; font-size: 11px; border-radius: 6px; }
                QPushButton:hover { background-color: #ef4444; }
            """)

    def update_display(self, q_img: QImage, status: dict):
        if not self.is_collapsed and self.camera_active:
            pixmap = QPixmap.fromImage(q_img).scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(pixmap)

        self.fps_label.setText(f"FPS: {status['fps']}")

        action_name = status['action']
        if status.get('is_left_click'):
            self.action_label.setText(">>> LEFT CLICK! <<<")
            self.action_label.setStyleSheet("color: #f43f5e; font-weight: bold; font-size: 11px;")
        elif status.get('is_right_click'):
            self.action_label.setText(">>> RIGHT CLICK! <<<")
            self.action_label.setStyleSheet("color: #f43f5e; font-weight: bold; font-size: 11px;")
        elif action_name == "MOVE":
            self.action_label.setText("ACTION: MOVING")
            self.action_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        elif "SCROLL" in action_name:
            self.action_label.setText(f"ACTION: {action_name}")
            self.action_label.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px;")
        else:
            self.action_label.setText(f"ACTION: {action_name}")
            self.action_label.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 11px;")

    def show_error(self, message: str):
        self.video_label.setText(f"Error: {message}")

    # Draggable Window support
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def close_app(self):
        if hasattr(self, 'worker'):
            self.worker.stop_camera()
        self.close()
        QtWidgets.QApplication.quit()


def launch_floating_widget():
    app = QtWidgets.QApplication(sys.argv)
    overlay = FloatingOverlay()
    overlay.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    launch_floating_widget()
