# ✋ Virtual Hand Cursor — Beginner-Friendly Project Guide

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand%20Tracking-orange.svg)](https://developers.google.com/mediapipe)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green.svg)](https://opencv.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-purple.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://microsoft.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An easy-to-use computer program that turns your normal webcam into an invisible mouse in the air. By moving your hand in front of the camera, you can move your computer cursor, click icons, drag files, right-click, and scroll through pages without touching any physical mouse!

---

## 🎓 Academic Project Details

- **Project Type**: Bachelor of Computer Applications (BCA) Project
- **College**: Vidyavahini First Grade & P.G. College, Tumakuru
- **University**: Affiliated to Tumkur University
- **Department**: Department of Computer Applications
- **Project Guide**: **Navyashree S**, Department of Computer Science
- **Student Team**:
  1. **Ananya M P** (Reg. No: `U11VU24S0036`)
  2. **Bhoomika** (Reg. No: `U11VU24S0349`)
  3. **Manasa K S** (Reg. No: `U11VU24S0070`)
  4. **Shubha C S** (Reg. No: `U11VU24S0304`)

---

## 📌 Table of Contents
1. [What is This Project? (The Simple Idea)](#-what-is-this-project-the-simple-idea)
2. [What is a "Module" in Python? (For Beginners)](#-what-is-a-module-in-python-for-beginners)
3. [The Tools We Used (Tech Stack Made Simple)](#-the-tools-we-used-tech-stack-made-simple)
4. [How It Works Step-by-Step (The Workflow)](#-how-it-works-step-by-step-the-workflow)
5. [How to Control the Mouse (Hand Gestures)](#-how-to-control-the-mouse-hand-gestures)
6. [The 7 Project Files Explained](#-the-7-project-files-explained)
7. [Simple Math Behind the Gestures](#-simple-math-behind-the-gestures)
8. [How to Download and Run It](#-how-to-download-and-run-it)
9. [Frequently Asked Questions (FAQ)](#-frequently-asked-questions-faq)

---

## 🌟 What is This Project? (The Simple Idea)

Usually, to move the mouse arrow on a computer screen, you have to hold a plastic mouse with your hand or slide your finger on a laptop touchpad.

**Our Virtual Hand Cursor does this completely touch-free:**
- You sit in front of your laptop or desktop webcam.
- You raise your hand in the air.
- When you move your index finger, the mouse arrow on your screen follows your finger smoothly like a laser pointer!
- When you pinch your thumb and index finger together, it performs a **Left Click**.
- When you pinch your thumb and pinky (small finger) together, it performs a **Right Click**.
- When you raise two fingers and glide up or down, it **Scrolls** the page.

### Real-World Uses:
1. **Cooking in the Kitchen**: Scroll through a recipe on your laptop without touching the screen with flour or oil on your fingers.
2. **Presentations**: Stand 5 feet away from your screen and control slides by pointing in the air.
3. **Clean Environments (Hospitals & Clinics)**: Doctors and dentists can view X-rays without touching unsterilized computer surfaces.
4. **Accessibility**: Useful for people who have difficulty gripping physical mice.

---

## 💡 What is a "Module" in Python? (For Beginners)

If you are new to programming, you will see the word **"module"** a lot. Here is what it means in simple English:

> 📘 **Simple Definition**:
> A **module** in Python is simply a single file containing Python code (a file that ends in `.py`).
>
> **Everyday Analogy**:
> Imagine you are building a toy car using Lego blocks:
> - You have one box for the wheels.
> - You have one box for the engine.
> - You have one box for the steering.
>
> In Python, instead of writing 3,000 lines of messy code inside one giant file, we divide the work into smaller, clean files called **modules**.
> - One module connects to the camera (`hand_detector.py`).
> - One module decides what gesture you made (`gesture_classifier.py`).
> - One module actually moves the Windows mouse cursor (`mouse_controller.py`).
>
> You can easily share and reuse code between files using the simple word: `import`.

---

## 🛠️ The Tools We Used (Tech Stack Made Simple)

We built this project using standard, reliable tools:

| Tool Name | What It Is in Plain English | What Job It Does Here |
| :--- | :--- | :--- |
| **Python** | The main programming language. | The central coordinator that links the camera, the math, and the mouse. |
| **OpenCV (`cv2`)** | Computer vision software (the computer's "eyes"). | Captures video frames from your webcam at 30 pictures per second and flips the image like a mirror. |
| **Google MediaPipe** | Hand tracking software created by Google. | Looks at each video frame and instantly finds 21 joint points on your hand (fingertips, knuckles, and wrist). |
| **PyQt6** | Modern desktop window toolkit. | Creates the clean dark-mode app window, the buttons, the camera preview, and the live status indicators. |
| **Windows API (`ctypes.user32`)** | Direct link into the Windows operating system. | Moves the actual Windows cursor and sends clicks with zero delay. |
| **1 Euro Filter** | A smart smoothing formula. | Eliminates tiny, involuntary hand shakes when you hover over small buttons. |

---

## 🔄 How It Works Step-by-Step (The Workflow)

Every single second, your computer repeats these **8 simple steps** 30 times:

```
[Webcam] ➡️ [Mirror Flip] ➡️ [Find 21 Hand Points] ➡️ [Filter Out Tremor]
                                                            ⬇️
[Click / Scroll] ⬅️ [Prevent Drift] ⬅️ [Check Gesture] ⬅️ [Map to Screen]
```

1. **Step 1: Video Capture**: The webcam takes a live photo 30 times a second.
2. **Step 2: Mirror Flip**: Webcams reverse your image. We flip it horizontally so when you move your hand to the right, your cursor moves to the right.
3. **Step 3: Finding Hand Points**: MediaPipe scans the image and marks 21 dots on your hand (wrist, knuckles, and fingertips).
4. **Step 4: Tremor Filtering**: Human hands naturally shake slightly in the air. The 1 Euro Filter algorithm locks the cursor still when you hover.
5. **Step 5: Screen Mapping**: If your hand moves 50% across the camera picture, the cursor is placed 50% across your computer monitor.
6. **Step 6: Gesture Recognition**: The computer checks which fingers are up and measures how close your fingertips are to your thumb.
7. **Step 7: Pre-Pinch Drift Prevention**: When humans pinch to click, the index finger curls slightly. The computer freezes the cursor right before the click hits, so you never miss your target button!
8. **Step 8: Mouse Action**: Windows receives the signal and performs the move, left-click, right-click, or scroll.

---

## 🖐️ How to Control the Mouse (Hand Gestures)

The software supports two modes: **Dual-Hand Mode** (recommended for best control) and **Single-Hand Fallback** (if only 1 hand is visible).

### 👑 Mode A: Dual-Hand Control (High Precision)
In Dual-Hand mode, your **Right Hand** is the pointer, and your **Left Hand** is the clicker:

| What to Do with Your Hand | What Happens on Your Computer |
| :--- | :--- |
| **Right Hand**: Extend index finger and point in the air. | **Moves the Cursor** smoothly across your screen. |
| **Left Hand**: Pinch **Thumb + Index finger** together. | **Left Click** (Selects an icon or button). |
| **Left Hand**: Pinch **Thumb + Index** and **hold** it while moving Right Hand. | **Drag & Drop** (Select text, move desktop icons, or drag windows). |
| **Left Hand**: Pinch **Thumb + Pinky (Small finger)** together. | **Right Click** (Opens right-click context menu). |
| **Left Hand**: Raise **Index + Middle fingers** together and swipe up/down. | **Scroll Wheel** (Scrolls web pages, PDFs, and spreadsheets). |

> 💡 **Why Pinky for Right Click?**  
> The index and middle fingers sit right next to each other, making them easy to confuse. The pinky finger is on the far opposite side of the hand, which completely prevents accidental clicks!

---

### ✋ Mode B: Single-Hand Fallback (Automatic)
If you are holding a cup of coffee with one hand, you can use just one hand for everything:

| Gesture | Action |
| :--- | :--- |
| Point with index finger | **Moves the cursor** |
| Pinch Thumb + Index finger | **Left Click** (Hold to drag) |
| Pinch Thumb + Pinky (Small finger) | **Right Click** |
| Raise Index + Middle fingers together and swipe | **Scroll Up / Down** |

---

## 📁 The 7 Project Files Explained

Here is where everything lives in the folder:

```
hand cursor/
├── HandCursor_Standalone.exe    # The ready-to-run app (Double-click to start, no Python needed!)
├── main.py                     # Starts the whole program
├── app_desktop.py              # Draws the desktop window and buttons
├── requirements.txt            # List of Python tools needed
├── hand_landmarker.task        # Google's hand-finding brain file
└── src/                        # Folder containing our 5 helper modules
    ├── config.py               # Holds settings (camera size, speed, click distance)
    ├── hand_detector.py        # Uses MediaPipe to find 21 hand points
    ├── gesture_classifier.py   # Decides if you are pointing, clicking, or scrolling
    ├── filter.py               # Removes hand shaking (1 Euro Filter)
    ├── mouse_controller.py     # Sends click and move commands to Windows
    └── visualizer.py           # Draws the hand skeleton and boxes on screen
```

---

## 📐 Simple Math Behind the Gestures

You do not need to be a math genius to understand how the computer measures your hand. Here are the simple formulas explained step-by-step:

### 1. Measuring Pinch Distance (Straight-Line Distance)
How does the computer know when two fingers touch? It uses the simple high-school Pythagorean theorem.

If your thumb tip is at $(X_1, Y_1)$ and your index tip is at $(X_2, Y_2)$:

```math
\text{Distance} = \sqrt{(X_2 - X_1)^2 + (Y_2 - Y_1)^2}
```

* **Left Click Rule**: When $\text{Distance} < 65\text{ pixels}$, your fingers are touching $\rightarrow$ **Left Click triggers!**
* **Right Click Rule**: When the distance between your **Thumb** and **Pinky (Small Finger)** $< 70\text{ pixels}$ $\rightarrow$ **Right Click triggers!**

---

### 2. Screen Coordinate Mapping (Scaling Camera to Monitor)
The camera picture is $1280 \times 720$ pixels, but your computer screen might be $1920 \times 1080$ pixels. The computer maps your hand position using simple proportional scaling:

```math
\text{Screen } X = \left( \frac{\text{Camera } X - \text{Margin}_X}{\text{Camera Width} - 2 \cdot \text{Margin}_X} \right) \times \text{Monitor Width}
```

```math
\text{Screen } Y = \left( \frac{\text{Camera } Y - \text{Margin}_Y}{\text{Camera Height} - 2 \cdot \text{Margin}_Y} \right) \times \text{Monitor Height}
```

* **Intuition**: If your hand moves $50\%$ across the camera frame, the mouse cursor moves to exactly $50\%$ across your computer screen.

---

### 3. Smooth Tremor Filter (1 Euro Filter)
When hovering your hand in the air, human fingers naturally shake by 1 to 2 pixels. To stop the cursor from vibrating, the computer dynamically filters the position:

```math
\text{Smooth Position}_t = \alpha \times \text{New Hand Position}_t + (1 - \alpha) \times \text{Previous Position}_{t-1}
```

Where $\alpha$ (responsiveness) adapts dynamically:
* **When Hand is Still / Hovering**: $\alpha$ decreases $\rightarrow$ **locks cursor 100% stable on buttons**.
* **When Hand Moves Fast**: $\alpha \to 1.0$ $\rightarrow$ **zero lag, cursor follows your hand instantly**.

---

### 4. Click Stability Lock (Two-Door Schmitt Trigger)
To prevent accidental double-clicks caused by tiny finger twitches, we use a two-door threshold rule:

```math
\text{Click State} = 
\begin{cases} 
\mathbf{CLICKED} & \text{if } \text{Distance} \le 65\text{ px} \\ 
\mathbf{RELEASED} & \text{if } \text{Distance} \ge 90\text{ px} \\ 
\text{Keep Current State} & \text{if } 65\text{ px} < \text{Distance} < 90\text{ px}
\end{cases}
```

* **Result**: Small hand twitches between $65\text{px}$ and $90\text{px}$ will never trigger accidental duplicate clicks!

---

## 🚀 How to Download and Run It

### Method 1: The Easiest Way (Double-Click `.exe`)
You don't need Python or any coding software:
1. Double-click **[`HandCursor_Standalone.exe`](HandCursor_Standalone.exe)** in the project folder.
2. The dark-mode window will open.
3. Click **"🎥 Enable Camera"**.
4. Raise your hand and start pointing!

---

### Method 2: Running with Python (For Programmers)
If you have Python installed:
1. Open your terminal in this project folder.
2. Install the required tools:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. Run the automated test suite (verifies everything works):
   ```bash
   python -m unittest discover tests
   ```

---

## ⌨️ Helpful Keyboard Shortcuts

- **`[Spacebar]`**: Instantly pause or resume mouse movement (useful when you want to rest your hand or type on your keyboard).
- **`[P]`**: Pin window so it stays on top of other apps.
- **`[C]`**: Turn the camera On or Off.

---

## ❓ Frequently Asked Questions (FAQ)

**Q1: Does this app send my webcam video to the internet?**  
**No.** 100% of the image processing happens directly on your own computer processor (CPU). No photos, videos, or personal data are ever saved or sent anywhere.

**Q2: Will it work with my laptop's built-in camera?**  
**Yes.** Any normal built-in webcam or USB plug-in camera works automatically.

**Q3: Can I reach all 4 corners of my computer screen?**  
**Yes.** We tuned the active frame and added Windows High-DPI support so the cursor easily reaches the top-left, top-right, bottom-left, and bottom-right corners without straining your arm.

---

## 📜 License
This project is open-source under the [MIT License](LICENSE).
