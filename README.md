# AI Virtual Hand Cursor Using Hand Gesture Recognition

A computer vision-based human-computer interaction system that turns webcam hand gestures into real-time mouse navigation and actions, eliminating the need for a physical mouse.

Based on the BCA Mini Project specification:
> **Institution:** Vidyavahini First Grade & P.G. College, Tumakuru (Affiliated to Tumkur University)  
> **Department:** Department of Computer Applications  
> **Project Guide:** Navyashree S (Department of Computer Science)  
> **Team Members:** Ananya M P, Bhoomika, Manasa K S, Shubha C S  

---

## 🌟 Key Features

- **Dual-Hand Control (High Precision)**:
  - **Right Hand**: Directs smooth cursor pointing with the index fingertip.
  - **Left Hand**: Triggers discrete mouse clicks and scrolls without moving or shaking the cursor.
- **Single-Hand Fallback**:
  - Automatically switches to single-hand gesture control if only one hand is raised in front of the camera.
- **Jitter-Free Movement**:
  - Exponential Moving Average (EMA) smoothing filter dampens hand micro-tremors for fluid pointer tracking.
- **Active Interaction Bounding Box**:
  - A calibrated active tracking zone allows reaching all 4 screen corners comfortably without extending hands out of camera view.
- **Real-Time Visual HUD Overlay**:
  - Displays hand skeleton landmarks, mode status, detected gesture actions, reticle crosshairs, and live FPS counter.
- **Safety Fail-Safe**:
  - Built-in PyAutoGUI fail-safe prevents mouse lockups. Quick exit by pressing `'q'`.

---

## 🖐️ Gesture Control Reference

### 1. Dual-Hand Mode (Recommended)

| Hand | Gesture | Action |
| :--- | :--- | :--- |
| **Right Hand** | Index finger pointing | **Move Cursor** |
| **Left Hand** | Pinch Thumb + Index finger | **Left Click** |
| **Left Hand** | Pinch Thumb + Middle finger | **Right Click** |
| **Left Hand** | Index & Middle fingers extended (Swipe Up/Down) | **Scroll Up / Down** |
| **Left Hand** | Open Palm / Rest | **Neutral / Hold Position** |

### 2. Single-Hand Mode (Fallback)

| Gesture | Action |
| :--- | :--- |
| Index finger up alone | **Move Cursor** |
| Pinch Thumb + Index finger | **Left Click** |
| Pinch Thumb + Middle finger | **Right Click** |
| Index + Middle fingers up together (Swipe Up/Down) | **Scroll Up / Down** |

---

## 📂 Project Architecture

```
hand cursor/
├── Synapsis.pdf                # Original Project Report / Synopsis
├── requirements.txt            # Python dependencies
├── main.py                     # Main application entry point
├── hand_landmarker.task        # MediaPipe Hand Landmark model file
├── src/
│   ├── __init__.py
│   ├── config.py               # Configurable thresholds, margins, smoothing, and colors
│   ├── hand_detector.py        # MediaPipe Tasks Vision wrapper (21 3D landmarks)
│   ├── gesture_classifier.py   # Dual-hand & single-hand gesture state machine
│   ├── mouse_controller.py     # Screen coordinate mapping, smoothing, PyAutoGUI actions
│   └── visualizer.py           # HUD overlay, skeleton bones, tracking box, FPS counter
└── tests/
    └── test_modules.py         # Automated unit test suite
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.8+ (Tested on Python 3.10 – 3.14)
- Standard USB or built-in webcam

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Automated Tests
```bash
python -m unittest discover tests
```

### 4. Standalone Windows Executable (.exe)

You can run the app directly without Python installed:
- **Single-File Executable**: [HandCursor_Standalone.exe](file:///d:/projects/hand%20cursor/HandCursor_Standalone.exe)
  - Completely self-contained single `.exe` file.
  - Can be shared directly via WhatsApp, Google Drive, or USB without any missing DLL errors.
- **Or via Python**:
  ```bash
  python main.py
  ```

### 🌟 Desktop App Features:
- **Zero Browser Dependencies**: Runs as a native Windows desktop GUI application.
- **Works Everywhere**: Operates globally across all applications, browsers (Chrome, Edge, Firefox), PDF viewers, and the Windows desktop.
- **Camera Under Your Control**: Camera starts **OFF** by default. Click **`🎥 Enable Camera`** to start tracking, and **`⏹ Stop Camera`** anytime to turn it off.
- **📌 Pinned Floating Mode**: Stays pinned on top of whatever app you are using so you can always see your tracking status. Click **`Unpinned`** to use it as a normal window.
- **Spacebar Shortcut**: Press **`Spacebar`** anytime to pause/resume mouse movement so you can type or rest your hands.
- **Native Win32 Precision**: Uses Windows User32 kernel events for 0ms lag pointer movement, clicks, and scrolling.

---

## ⚙️ Configuration (`src/config.py`)

You can customize camera settings, thresholds, and smoothing parameters in `src/config.py`:

```python
# Screen Margins (Active Bounding Box)
MARGIN_X = 100       # Horizontal margin from camera edge
MARGIN_Y = 80        # Vertical margin from camera edge

# Smoothing
SMOOTHING_FACTOR = 4 # Higher = smoother cursor, lower = faster response

# Pinch Sensitivity
PINCH_THRESHOLD_CLICK = 38     # Distance in pixels to trigger left click
PINCH_THRESHOLD_RIGHT = 38     # Distance in pixels to trigger right click

# Cooldowns (seconds)
CLICK_COOLDOWN = 0.35          # Debounce delay between successive clicks
```

---

## 📋 System Modules (From Project Synopsis)

1. **Video Capture**: OpenCV captures live frames from the webcam.
2. **Hand Detection**: MediaPipe hand-tracking framework detects up to 2 hands simultaneously.
3. **Hand Landmark Tracking**: Identifies 21 keypoints including fingertips and joints.
4. **Gesture Recognition**: Evaluates finger extension geometry and pinch distances.
5. **Cursor Control**: Maps normalized fingertip coordinates to full monitor resolution with smoothing.
6. **Mouse Action Control**: Triggers OS mouse events (left click, right click, scroll).
7. **Visual Feedback**: Real-time HUD overlay rendering hand skeletons, status cues, and FPS.
