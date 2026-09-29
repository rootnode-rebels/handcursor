"""
Flask Web Dashboard for AI Virtual Hand Cursor.
Camera is in 100% control of the user:
- Camera is OFF by default.
- Website asks for user permission and requires user to click 'Enable Camera'.
- User can click 'Stop Camera' anytime to instantly turn off webcam hardware.
- Automatically releases camera if browser tab is closed (beforeunload beacon).
"""
import time
import threading
import traceback
from flask import Flask, Response, render_template_string, jsonify, request
import cv2
import numpy as np

from src.config import CAMERA_ID, CAMERA_BACKEND, FRAME_WIDTH, FRAME_HEIGHT
from src.hand_detector import HandDetector
from src.gesture_classifier import GestureClassifier, GestureAction
from src.mouse_controller import MouseController
from src.visualizer import Visualizer

app = Flask(__name__)


class UserControlledCameraStreamer:
    """Manages webcam lifecycle strictly based on user explicit permission and commands."""

    def __init__(self):
        self.lock = threading.Lock()
        self.cap = None
        self.running = False
        self.thread = None
        self.latest_jpeg = None
        self.mouse_enabled = True
        self.state = {
            "camera_active": False,
            "fps": 0.0,
            "mode": "Camera Off",
            "action": "IDLE",
            "mouse_enabled": True
        }

    def start_camera(self) -> bool:
        with self.lock:
            if self.running:
                return True

            print(f"[USER COMMAND] User requested camera start. Opening camera {CAMERA_ID}...")
            self.cap = cv2.VideoCapture(CAMERA_ID, CAMERA_BACKEND)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

            if not self.cap.isOpened():
                print("[ERROR] Failed to open camera device.")
                self.cap = None
                return False

            self.running = True
            self.state["camera_active"] = True
            self.state["mode"] = "Initializing Hand Tracking..."
            self.thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.thread.start()
            print("[SUCCESS] Camera activated upon user permission.")
            return True

    def stop_camera(self) -> bool:
        with self.lock:
            if not self.running and self.cap is None:
                return True

            print("[USER COMMAND] User requested camera stop. Releasing hardware...")
            self.running = False
            self.latest_jpeg = None
            if self.cap is not None:
                self.cap.release()
                self.cap = None

            self.state = {
                "camera_active": False,
                "fps": 0.0,
                "mode": "Camera Off",
                "action": "IDLE",
                "mouse_enabled": self.mouse_enabled
            }
            print("[SUCCESS] Camera hardware completely stopped and released.")
            return True

    def _worker_loop(self):
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

                # Mouse Control
                if self.mouse_enabled:
                    screen_pos, _ = mouse.execute_action(cursor_pos, action)
                else:
                    mouse.is_left_clicked = False
                    mouse.is_right_clicked = False

                self.state = {
                    "camera_active": True,
                    "fps": round(fps, 1),
                    "mode": debug_info.get("mode", "Tracking"),
                    "action": action.name,
                    "mouse_enabled": self.mouse_enabled
                }

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

                # Encode to JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    jpeg_bytes = buffer.tobytes()
                    with self.lock:
                        self.latest_jpeg = jpeg_bytes

                time.sleep(0.01)

        except Exception as e:
            print("Exception in camera thread:", e)
            traceback.print_exc()
        finally:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            detector.close()
            self.running = False
            self.state["camera_active"] = False

    def get_frame(self):
        with self.lock:
            return self.latest_jpeg


streamer = UserControlledCameraStreamer()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Virtual Hand Cursor Dashboard</title>
    <style>
        :root {
            --bg: #0b1120;
            --card-bg: #1e293b;
            --card-border: #334155;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
        
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--card-border); padding-bottom: 16px; }
        header h1 { font-size: 1.4rem; display: flex; align-items: center; gap: 10px; }
        .header-controls { display: flex; align-items: center; gap: 12px; }

        .btn {
            padding: 9px 16px; border-radius: 8px; border: none; font-size: 0.9rem; font-weight: 600; cursor: pointer;
            display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s ease;
        }
        .btn-primary { background: #0284c7; color: white; }
        .btn-primary:hover { background: #0369a1; }
        .btn-success { background: var(--success); color: white; }
        .btn-success:hover { background: #16a34a; }
        .btn-danger { background: var(--danger); color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text); }
        .btn-outline:hover { background: #334155; }

        .status-badge {
            font-size: 0.8rem; padding: 5px 12px; border-radius: 9999px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px;
        }
        .badge-off { background: #334155; color: #94a3b8; }
        .badge-on { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }

        .main-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
        @media (max-width: 900px) { .main-layout { grid-template-columns: 1fr; } }

        .video-card { background: var(--card-bg); border-radius: 14px; overflow: hidden; border: 1px solid var(--card-border); }
        .video-header { padding: 12px 16px; background: #0f172a; border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center; }
        .video-container { position: relative; width: 100%; min-height: 480px; background: #020617; display: flex; align-items: center; justify-content: center; }
        .video-stream { width: 100%; height: auto; max-height: 500px; object-fit: contain; }

        /* Permission & Inactive Screen */
        .permission-screen {
            padding: 40px 24px; text-align: center; max-width: 440px; display: flex; flex-direction: column; align-items: center; gap: 16px;
        }
        .icon-circle {
            width: 72px; height: 72px; border-radius: 50%; background: #1e293b; border: 2px solid #334155;
            display: flex; align-items: center; justify-content: center; font-size: 32px;
        }
        .permission-title { font-size: 1.25rem; font-weight: 700; color: #f8fafc; }
        .permission-desc { font-size: 0.9rem; color: var(--text-dim); line-height: 1.5; }

        .sidebar { display: flex; flex-direction: column; gap: 16px; }
        .card { background: var(--card-bg); border-radius: 14px; padding: 18px; border: 1px solid var(--card-border); }
        .card h2 { font-size: 1.05rem; margin-bottom: 12px; color: var(--accent); }

        .toggle-btn {
            width: 100%; padding: 12px; border-radius: 8px; border: none; font-size: 0.95rem; font-weight: 600; cursor: pointer;
            transition: all 0.2s ease;
        }
        .toggle-on { background: #16a34a; color: white; }
        .toggle-off { background: #b91c1c; color: white; }

        .status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
        .status-item { background: #0f172a; padding: 10px; border-radius: 8px; border: 1px solid var(--card-border); }
        .status-label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; }
        .status-val { font-size: 1.05rem; font-weight: 700; margin-top: 4px; color: var(--accent); }

        .gesture-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }
        .gesture-table th, .gesture-table td { padding: 8px 6px; text-align: left; border-bottom: 1px solid var(--card-border); }
        .gesture-table th { color: var(--text-dim); font-size: 0.75rem; }
        .tag-right { color: #4ade80; font-weight: 600; }
        .tag-left { color: #f472b6; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>✋ AI Virtual Hand Cursor</h1>
            <div class="header-controls">
                <span id="cameraBadge" class="status-badge badge-off">● Camera Off</span>
                <button id="btnHeaderAction" class="btn btn-primary" onclick="requestAndStartCamera()">
                    🎥 Enable Camera
                </button>
            </div>
        </header>

        <div class="main-layout">
            <!-- Left: Video Area -->
            <div class="video-card">
                <div class="video-header">
                    <span>Webcam Landmark Feed</span>
                    <span id="fpsDisplay" style="color: #4ade80; font-weight: 700;">FPS: --</span>
                </div>
                <div class="video-container" id="videoContainer">
                    <!-- Shown when Camera is OFF -->
                    <div id="permissionPrompt" class="permission-screen">
                        <div class="icon-circle">🔒</div>
                        <h2 class="permission-title">Camera Permission Required</h2>
                        <p class="permission-desc">
                            Your camera is currently <strong>inactive</strong> and safely turned off.
                            Click below to grant camera access and activate the AI gesture cursor.
                        </p>
                        <button class="btn btn-success" style="padding: 12px 24px; font-size: 1rem;" onclick="requestAndStartCamera()">
                            ✓ Allow & Enable Camera
                        </button>
                    </div>

                    <!-- Shown when Camera is ON -->
                    <img id="videoStream" class="video-stream" style="display: none;" alt="Webcam Feed">
                </div>
            </div>

            <!-- Right: Controls -->
            <div class="sidebar">
                <!-- Camera Master Control Card -->
                <div class="card">
                    <h2>Camera Hardware Control</h2>
                    <p style="font-size: 0.85rem; color: var(--text-dim); margin-bottom: 12px;">
                        You have complete control over your webcam. Stop it at any moment to turn off your camera device completely.
                    </p>
                    <div style="display: flex; gap: 10px;">
                        <button id="btnStart" class="btn btn-primary" style="flex: 1;" onclick="requestAndStartCamera()">
                            Start Camera
                        </button>
                        <button id="btnStop" class="btn btn-danger" style="flex: 1;" onclick="stopCamera()" disabled>
                            Stop Camera
                        </button>
                    </div>
                </div>

                <!-- Mouse Toggle Card -->
                <div class="card">
                    <h2>Mouse Control Switch</h2>
                    <p style="font-size: 0.85rem; color: var(--text-dim); margin-bottom: 12px;">
                        Toggle physical mouse movement on or off while keeping the camera tracking preview active.
                    </p>
                    <button id="toggleBtn" class="toggle-btn toggle-on" onclick="toggleMouse()">
                        Mouse Control: ENABLED
                    </button>
                    <div class="status-grid">
                        <div class="status-item">
                            <div class="status-label">Current Action</div>
                            <div id="actionDisplay" class="status-val">IDLE</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">Tracking Mode</div>
                            <div id="modeDisplay" class="status-val" style="font-size: 0.85rem;">Camera Off</div>
                        </div>
                    </div>
                </div>

                <!-- Gesture Reference -->
                <div class="card">
                    <h2>Gesture Reference</h2>
                    <table class="gesture-table">
                        <thead>
                            <tr>
                                <th>Hand</th>
                                <th>Gesture</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="tag-right">Right</td>
                                <td>Index Finger</td>
                                <td><strong>Move Pointer</strong></td>
                            </tr>
                            <tr>
                                <td class="tag-left">Left</td>
                                <td>Thumb + Index Pinch</td>
                                <td><strong>Left Click</strong></td>
                            </tr>
                            <tr>
                                <td class="tag-left">Left</td>
                                <td>Thumb + Middle Pinch</td>
                                <td><strong>Right Click</strong></td>
                            </tr>
                            <tr>
                                <td class="tag-left">Left</td>
                                <td>2 Fingers Up/Down</td>
                                <td><strong>Scroll</strong></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const imgElement = document.getElementById('videoStream');
        const permissionPrompt = document.getElementById('permissionPrompt');
        const cameraBadge = document.getElementById('cameraBadge');
        const btnHeaderAction = document.getElementById('btnHeaderAction');
        const btnStart = document.getElementById('btnStart');
        const btnStop = document.getElementById('btnStop');

        let isCameraActive = false;
        let isFetching = false;

        // 1. Request Browser Camera Permission, then enable on backend
        async function requestAndStartCamera() {
            try {
                // Request native browser permission prompt
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                // Stop local browser test stream immediately once allowed
                stream.getTracks().forEach(track => track.stop());

                // Inform backend to open hardware camera
                const res = await fetch('/api/start_camera', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'started') {
                    setCameraActiveUI(true);
                    fetchNextFrame();
                }
            } catch (err) {
                alert("Camera permission was denied or camera is unavailable: " + err.message);
            }
        }

        // 2. Stop Camera immediately
        async function stopCamera() {
            try {
                await fetch('/api/stop_camera', { method: 'POST' });
                setCameraActiveUI(false);
            } catch (err) {
                console.error("Error stopping camera:", err);
            }
        }

        function setCameraActiveUI(active) {
            isCameraActive = active;
            if (active) {
                cameraBadge.className = 'status-badge badge-on';
                cameraBadge.innerText = '● Camera Active';
                btnHeaderAction.className = 'btn btn-danger';
                btnHeaderAction.innerText = '⏹ Stop Camera';
                btnHeaderAction.onclick = stopCamera;
                btnStart.disabled = true;
                btnStop.disabled = false;
                permissionPrompt.style.display = 'none';
                imgElement.style.display = 'block';
            } else {
                cameraBadge.className = 'status-badge badge-off';
                cameraBadge.innerText = '● Camera Off';
                btnHeaderAction.className = 'btn btn-primary';
                btnHeaderAction.innerText = '🎥 Enable Camera';
                btnHeaderAction.onclick = requestAndStartCamera;
                btnStart.disabled = false;
                btnStop.disabled = true;
                permissionPrompt.style.display = 'flex';
                imgElement.style.display = 'none';
                document.getElementById('fpsDisplay').innerText = 'FPS: --';
                document.getElementById('actionDisplay').innerText = 'IDLE';
                document.getElementById('modeDisplay').innerText = 'Camera Off';
            }
        }

        function fetchNextFrame() {
            if (!isCameraActive || isFetching) return;
            isFetching = true;
            fetch('/current_frame?t=' + Date.now())
                .then(response => {
                    if (!response.ok) throw new Error("Frame not ready");
                    return response.blob();
                })
                .then(blob => {
                    if (!isCameraActive) {
                        isFetching = false;
                        return;
                    }
                    const objectUrl = URL.createObjectURL(blob);
                    imgElement.onload = () => {
                        URL.revokeObjectURL(objectUrl);
                        isFetching = false;
                        if (isCameraActive) {
                            requestAnimationFrame(fetchNextFrame);
                        }
                    };
                    imgElement.src = objectUrl;
                })
                .catch(() => {
                    isFetching = false;
                    if (isCameraActive) {
                        setTimeout(fetchNextFrame, 150);
                    }
                });
        }

        function toggleMouse() {
            fetch('/api/toggle_mouse', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    const btn = document.getElementById('toggleBtn');
                    if (data.mouse_enabled) {
                        btn.className = 'toggle-btn toggle-on';
                        btn.innerText = 'Mouse Control: ENABLED';
                    } else {
                        btn.className = 'toggle-btn toggle-off';
                        btn.innerText = 'Mouse Control: DISABLED (Preview Only)';
                    }
                });
        }

        // Status Polling
        setInterval(() => {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    if (data.camera_active !== isCameraActive) {
                        setCameraActiveUI(data.camera_active);
                    }
                    if (data.camera_active) {
                        document.getElementById('fpsDisplay').innerText = 'FPS: ' + data.fps;
                        document.getElementById('actionDisplay').innerText = data.action;
                        document.getElementById('modeDisplay').innerText = data.mode;
                    }
                })
                .catch(() => {});
        }, 600);

        // Turn off camera automatically if tab is closed or navigated away
        window.addEventListener('beforeunload', () => {
            navigator.sendBeacon('/api/stop_camera');
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/start_camera', methods=['POST'])
def start_camera():
    success = streamer.start_camera()
    return jsonify({"status": "started" if success else "error"})


@app.route('/api/stop_camera', methods=['POST'])
def stop_camera():
    streamer.stop_camera()
    return jsonify({"status": "stopped"})


@app.route('/current_frame')
def current_frame():
    frame = streamer.get_frame()
    if frame is None:
        # Placeholder when camera is off
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(dummy, "Camera Inactive", (220, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        _, buf = cv2.imencode('.jpg', dummy)
        frame = buf.tobytes()

    return Response(frame, mimetype='image/jpeg')


@app.route('/api/status')
def get_status():
    return jsonify(streamer.state)


@app.route('/api/toggle_mouse', methods=['POST'])
def toggle_mouse():
    streamer.mouse_enabled = not streamer.mouse_enabled
    streamer.state["mouse_enabled"] = streamer.mouse_enabled
    return jsonify({"mouse_enabled": streamer.mouse_enabled})


if __name__ == '__main__':
    print("Starting AI Virtual Hand Cursor Web Server (Camera OFF by default)...")
    print("Web dashboard accessible at: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
