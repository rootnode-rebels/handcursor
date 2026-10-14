"""
PDF Project Report Generator for AI Virtual Hand Cursor Using Hand Gesture Recognition.
Uses ReportLab to generate a high-quality, professional academic report.
"""
import os
import sys
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically and adds running headers & footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        if self._pageNumber == 1:
            # Skip cover page
            return

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header
        self.drawString(54, 11 * inch - 36, "AI Virtual Hand Cursor Using Hand Gesture Recognition — Project Report")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_str)
        self.drawString(54, 36, "Vidyavahini First Grade & P.G. College | BCA Mini Project")
        self.line(54, 46, 8.5 * inch - 54, 46)

        self.restoreState()


def build_pdf(filename="AI_Virtual_Hand_Cursor_Project_Report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    c_primary = colors.HexColor("#0f172a")
    c_accent = colors.HexColor("#0284c7")
    c_text = colors.HexColor("#1e293b")

    style_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=28,
        textColor=c_primary,
        alignment=1, # Center
        spaceAfter=15
    )

    style_subtitle = ParagraphStyle(
        'CoverSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        alignment=1,
        spaceAfter=25
    )

    style_h1 = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=20,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=c_text,
        spaceAfter=8
    )

    style_formula = ParagraphStyle(
        'Formula_Custom',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f766e"),
        leftIndent=15,
        spaceAfter=6
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=c_text
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("VIDYAVAHINI GROUP OF INSTITUTIONS", ParagraphStyle('InstHeader', fontName='Helvetica-Bold', fontSize=13, alignment=1, textColor=c_primary, leading=16)))
    story.append(Paragraph("VIDYAVAHINI FIRST GRADE & P.G. COLLEGE", ParagraphStyle('CollegeHeader', fontName='Helvetica-Bold', fontSize=15, alignment=1, textColor=c_primary, leading=18)))
    story.append(Paragraph("Affiliated to Tumkur University", ParagraphStyle('Affil', fontName='Helvetica', fontSize=10, alignment=1, textColor=colors.HexColor("#64748b"), leading=13)))
    story.append(Spacer(1, 40))

    story.append(Paragraph("PROJECT REPORT ON", ParagraphStyle('ReportOn', fontName='Helvetica', fontSize=11, alignment=1, textColor=colors.HexColor("#475569"), leading=14)))
    story.append(Paragraph("MINI PROJECT", ParagraphStyle('MiniProj', fontName='Helvetica-Bold', fontSize=13, alignment=1, textColor=c_accent, leading=16)))
    story.append(Spacer(1, 15))

    story.append(Paragraph("AI Virtual Hand Cursor Using Hand Gesture Recognition", style_title))
    story.append(Paragraph("Touch-Free Human-Computer Interaction Powered by Computer Vision & MediaPipe", style_subtitle))
    story.append(HRFlowable(width="60%", thickness=1.5, color=c_accent, spaceBefore=5, spaceAfter=30))

    # Students & Guide Table
    cover_data = [
        [
            Paragraph("<b>Submitted By:</b>", style_body),
            Paragraph("<b>Under the Guidance of:</b>", style_body)
        ],
        [
            Paragraph("• <b>Ananya M P</b> (U11VU24S0036)<br/>"
                      "• <b>Bhoomika</b> (U11VU24S0349)<br/>"
                      "• <b>Manasa K S</b> (U11VU24S0070)<br/>"
                      "• <b>Shubha C S</b> (U11VU24S0304)", style_body),
            Paragraph("<b>Navyashree S</b><br/>"
                      "Department of Computer Science<br/>"
                      "Vidyavahini First Grade & P.G. College<br/>"
                      "Tumakuru", style_body)
        ]
    ]

    t_cover = Table(cover_data, colWidths=[3.25 * inch, 3.25 * inch])
    t_cover.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(t_cover)

    story.append(Spacer(1, 60))
    story.append(Paragraph("DEPARTMENT OF COMPUTER APPLICATIONS", ParagraphStyle('Dept', fontName='Helvetica-Bold', fontSize=11, alignment=1, textColor=c_primary)))
    story.append(Paragraph("TUMAKURU, KARNATAKA", ParagraphStyle('Place', fontName='Helvetica', fontSize=10, alignment=1, textColor=colors.HexColor("#64748b"))))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 1: ABSTRACT & INTRODUCTION
    # =========================================================================
    story.append(Paragraph("1. Abstract & Introduction", style_h1))
    story.append(Paragraph(
        "The <b>AI Virtual Hand Cursor</b> is an artificial intelligence and computer vision-based system "
        "engineered to control operating system mouse operations using touch-free hand gestures. "
        "Standard computer setups require continuous physical contact with peripherals such as a mouse or trackpad, "
        "which can cause fatigue, hardware breakdown, or inconvenience in touch-free environments. "
        "This project captures video via a webcam and processes frames in real-time utilizing Python, OpenCV, and MediaPipe. "
        "A 21-point hand landmark estimation pipeline detects spatial finger configurations and calculates precise gestures. "
        "These are then mapped directly to virtual cursor navigation, left-click, right-click, and scrolling via "
        "operating system kernel events and PyAutoGUI.",
        style_body
    ))

    # =========================================================================
    # SECTION 2: PROBLEM STATEMENT & COMPARISON
    # =========================================================================
    story.append(Paragraph("2. Existing System vs. Proposed System", style_h1))
    
    comp_data = [
        [Paragraph("Feature / Aspect", style_table_header), Paragraph("Existing System (Physical Mouse)", style_table_header), Paragraph("Proposed System (AI Virtual Cursor)", style_table_header)],
        [Paragraph("Physical Contact", style_table_cell), Paragraph("Requires constant hand contact with surface.", style_table_cell), Paragraph("Completely touch-free; operates in open air.", style_table_cell)],
        [Paragraph("Hardware Dependency", style_table_cell), Paragraph("Requires physical mouse, mousepad, batteries/wire.", style_table_cell), Paragraph("Uses existing built-in or USB webcam.", style_table_cell)],
        [Paragraph("Hardware Failure", style_table_cell), Paragraph("Switches fail, cables fray, optical sensors collect dust.", style_table_cell), Paragraph("Zero moving physical parts; pure software.", style_table_cell)],
        [Paragraph("Hygiene & Accessibility", style_table_cell), Paragraph("Transmits germs; unsuitable for sterile/medical areas.", style_table_cell), Paragraph("Sterile, hygienic, accessible for touch-free computing.", style_table_cell)],
        [Paragraph("Portability", style_table_cell), Paragraph("Extra accessory to carry and connect.", style_table_cell), Paragraph("Runs directly on laptop/PC hardware.", style_table_cell)]
    ]
    t_comp = Table(comp_data, colWidths=[1.8 * inch, 2.4 * inch, 2.8 * inch])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 12))

    # =========================================================================
    # SECTION 3: THE 7 CORE MODULES
    # =========================================================================
    story.append(Paragraph("3. Detailed Module Architecture", style_h1))
    story.append(Paragraph("As specified in Section 5 of the project synopsis, the system comprises 7 functional modules:", style_body))

    modules_data = [
        [Paragraph("No.", style_table_header), Paragraph("Module Name", style_table_header), Paragraph("Implementation Details & Technical Role", style_table_header)],
        [Paragraph("1", style_table_cell), Paragraph("<b>Video Capture</b>", style_table_cell), Paragraph("OpenCV captures live video frames via DirectShow (<code>cv2.CAP_DSHOW</code>) at 30 FPS, avoiding Windows Media Foundation deadlocks.", style_table_cell)],
        [Paragraph("2", style_table_cell), Paragraph("<b>Hand Detection</b>", style_table_cell), Paragraph("MediaPipe Tasks Vision locates hands in each frame using lightweight convolutional networks optimized with CPU XNNPACK.", style_table_cell)],
        [Paragraph("3", style_table_cell), Paragraph("<b>Landmark Tracking</b>", style_table_cell), Paragraph("Extracts 21 3D landmarks (x, y, z) per hand, tracking fingertips (Thumb 4, Index 8, Middle 12, Ring 16, Pinky 20) and joints.", style_table_cell)],
        [Paragraph("4", style_table_cell), Paragraph("<b>Gesture Recognition</b>", style_table_cell), Paragraph("Evaluates geometric finger extension ($y_{tip} < y_{pip}$) and Euclidean pinch thresholds ($d < 38px$) to determine active commands.", style_table_cell)],
        [Paragraph("5", style_table_cell), Paragraph("<b>Cursor Control</b>", style_table_cell), Paragraph("Maps active camera boundary coordinates to screen pixels using linear interpolation, adaptive smoothing, and tremor deadzone filtering.", style_table_cell)],
        [Paragraph("6", style_table_cell), Paragraph("<b>Mouse Action Control</b>", style_table_cell), Paragraph("Converts gestures into left-clicks, right-clicks, and scrolling via native Win32 User32 APIs and PyAutoGUI with click-lock freezing.", style_table_cell)],
        [Paragraph("7", style_table_cell), Paragraph("<b>Visual Feedback</b>", style_table_cell), Paragraph("Renders real-time HUD overlays: hand skeleton bones, golden active box, dynamic glowing action banners, and live FPS.", style_table_cell)]
    ]
    t_mod = Table(modules_data, colWidths=[0.4 * inch, 1.8 * inch, 4.8 * inch])
    t_mod.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_mod)
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 4: MATHEMATICAL MODELING & ALGORITHMS
    # =========================================================================
    story.append(Paragraph("4. Mathematical Formulations & Signal Processing", style_h1))
    
    story.append(Paragraph("<b>A. Euclidean Distance Metric for Pinch Detection:</b>", style_body))
    story.append(Paragraph("The spatial Euclidean distance $d$ between landmark points $P_1(x_1, y_1)$ and $P_2(x_2, y_2)$ is defined as:", style_body))
    story.append(Paragraph("d(P_1, P_2) = sqrt((x_2 - x_1)^2 + (y_2 - y_1)^2)", style_formula))
    story.append(Paragraph("• <b>Left Click Trigger</b>: If d(Thumb_4, Index_8) < 38 pixels.<br/>"
                           "• <b>Right Click Trigger</b>: If d(Thumb_4, Middle_12) < 38 pixels.", style_body))

    story.append(Paragraph("<b>B. Active Frame Coordinate Linear Projection:</b>", style_body))
    story.append(Paragraph("Camera margins $M_x = 100px, M_y = 80px$ ensure reaching monitor corners comfortably without reaching frame borders:", style_body))
    story.append(Paragraph("S_x = ((C_x - M_x) / (W_cam - 2*M_x)) * Screen_Width", style_formula))
    story.append(Paragraph("S_y = ((C_y - M_y) / (H_cam - 2*M_y)) * Screen_Height", style_formula))

    story.append(Paragraph("<b>C. Speed-Adaptive Exponential Moving Average (EMA) Smoothing:</b>", style_body))
    story.append(Paragraph("To reconcile smooth tracking with responsiveness, smoothing factor $\\alpha$ adapts to motion velocity $\\Delta$:", style_body))
    story.append(Paragraph("P_t = P_{t-1} + (S_t - P_{t-1}) / alpha", style_formula))
    story.append(Paragraph("• If velocity $\\Delta > 60px$: $\\alpha = 3$ (Ultra-fast responsive tracking across screen).<br/>"
                           "• If velocity $\\Delta < 20px$: $\\alpha = 7$ (High-damping stability over small icons/buttons).", style_body))

    story.append(Paragraph("<b>D. Involuntary Tremor Deadzone Filter & Click-Lock Freezing:</b>", style_body))
    story.append(Paragraph("• <b>Deadzone Suppression</b>: If $|S_t - P_{t-1}| < 8px$, the position is held constant: $P_t = P_{t-1}$.<br/>"
                           "• <b>Click-Lock Freezing</b>: The moment a pinch click occurs, coordinates are locked at target position for $0.35s$. "
                           "This completely eliminates the natural involuntary finger displacement that causes target drift when clicking buttons.", style_body))
    story.append(Spacer(1, 10))

    # =========================================================================
    # SECTION 5: GESTURE CONTROL MATRIX
    # =========================================================================
    story.append(Paragraph("5. Gesture Interaction Schema", style_h1))
    
    gest_data = [
        [Paragraph("Mode", style_table_header), Paragraph("Hand Assigned", style_table_header), Paragraph("Hand Gesture / Posture", style_table_header), Paragraph("Dispatched Mouse Operation", style_table_header)],
        [Paragraph("Dual-Hand (Default)", style_table_cell), Paragraph("Right Hand", style_table_cell), Paragraph("Index finger extended pointing", style_table_cell), Paragraph("<b>Move Pointer</b> across desktop", style_table_cell)],
        [Paragraph("Dual-Hand (Default)", style_table_cell), Paragraph("Left Hand", style_table_cell), Paragraph("Pinch Thumb (4) + Index (8)", style_table_cell), Paragraph("<b>Left Click</b> (Locks position)", style_table_cell)],
        [Paragraph("Dual-Hand (Default)", style_table_cell), Paragraph("Left Hand", style_table_cell), Paragraph("Pinch Thumb (4) + Middle (12)", style_table_cell), Paragraph("<b>Right Click</b> (Context Menu)", style_table_cell)],
        [Paragraph("Dual-Hand (Default)", style_table_cell), Paragraph("Left Hand", style_table_cell), Paragraph("Index + Middle fingers swipe vertical", style_table_cell), Paragraph("<b>Scroll Up / Down</b>", style_table_cell)],
        [Paragraph("Dual-Hand (Default)", style_table_cell), Paragraph("Left Hand", style_table_cell), Paragraph("Open Palm / Hand at rest", style_table_cell), Paragraph("<b>Neutral / Hover Position</b>", style_table_cell)],
        [Paragraph("Single-Hand (Fallback)", style_table_cell), Paragraph("Either Hand", style_table_cell), Paragraph("Index finger alone extended", style_table_cell), Paragraph("<b>Move Pointer</b>", style_table_cell)],
        [Paragraph("Single-Hand (Fallback)", style_table_cell), Paragraph("Either Hand", style_table_cell), Paragraph("Pinch Thumb + Index finger", style_table_cell), Paragraph("<b>Left Click</b>", style_table_cell)],
        [Paragraph("Single-Hand (Fallback)", style_table_cell), Paragraph("Either Hand", style_table_cell), Paragraph("Pinch Thumb + Middle finger", style_table_cell), Paragraph("<b>Right Click</b>", style_table_cell)],
        [Paragraph("Single-Hand (Fallback)", style_table_cell), Paragraph("Either Hand", style_table_cell), Paragraph("Index + Middle fingers extended", style_table_cell), Paragraph("<b>Scroll Up / Down</b>", style_table_cell)]
    ]
    t_gest = Table(gest_data, colWidths=[1.5 * inch, 1.2 * inch, 2.3 * inch, 2.0 * inch])
    t_gest.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_gest)
    story.append(Spacer(1, 12))

    # =========================================================================
    # SECTION 6: SYSTEM REQUIREMENTS
    # =========================================================================
    story.append(Paragraph("6. Hardware and Software Requirements", style_h1))
    
    req_data = [
        [Paragraph("Category", style_table_header), Paragraph("Component", style_table_header), Paragraph("Specification / Minimum Requirement", style_table_header), Paragraph("Role in System", style_table_header)],
        [Paragraph("Hardware", style_table_cell), Paragraph("Processor", style_table_cell), Paragraph("Intel Core i3 2.0 GHz or AMD equivalent", style_table_cell), Paragraph("Processes vision frames and ML tensors", style_table_cell)],
        [Paragraph("Hardware", style_table_cell), Paragraph("Memory (RAM)", style_table_cell), Paragraph("Minimum 4 GB (8 GB Recommended)", style_table_cell), Paragraph("Holds video buffer and GUI structures", style_table_cell)],
        [Paragraph("Hardware", style_table_cell), Paragraph("Webcam", style_table_cell), Paragraph("Built-in or External USB (720p / 480p, 30 FPS)", style_table_cell), Paragraph("Captures optical input frames", style_table_cell)],
        [Paragraph("Hardware", style_table_cell), Paragraph("Storage", style_table_cell), Paragraph("Minimum 500 MB free space", style_table_cell), Paragraph("Application files, model weights, dependencies", style_table_cell)],
        [Paragraph("Software", style_table_cell), Paragraph("Operating System", style_table_cell), Paragraph("Windows 10 / Windows 11 (64-bit) or Linux", style_table_cell), Paragraph("Host operating environment", style_table_cell)],
        [Paragraph("Software", style_table_cell), Paragraph("Programming Language", style_table_cell), Paragraph("Python 3.10 – 3.14", style_table_cell), Paragraph("Core development and algorithmic logic", style_table_cell)],
        [Paragraph("Software", style_table_cell), Paragraph("OpenCV", style_table_cell), Paragraph("opencv-python >= 4.8.0", style_table_cell), Paragraph("Frame capture, color conversion, HUD rendering", style_table_cell)],
        [Paragraph("Software", style_table_cell), Paragraph("MediaPipe", style_table_cell), Paragraph("mediapipe >= 1.0.0 (Tasks Vision)", style_table_cell), Paragraph("Hand detection & 21 3D landmark tracking", style_table_cell)],
        [Paragraph("Software", style_table_cell), Paragraph("PyAutoGUI / Win32", style_table_cell), Paragraph("pyautogui >= 0.9.54 & User32 kernel", style_table_cell), Paragraph("Dispatches hardware mouse events", style_table_cell)],
        [Paragraph("Software", style_table_cell), Paragraph("PyQt6", style_table_cell), Paragraph("PyQt6 >= 6.11.0", style_table_cell), Paragraph("Modern GUI desktop interface & floating HUD", style_table_cell)]
    ]
    t_req = Table(req_data, colWidths=[1.1 * inch, 1.4 * inch, 2.5 * inch, 2.0 * inch])
    t_req.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_req)
    story.append(Spacer(1, 12))

    # =========================================================================
    # SECTION 7: TESTING & VERIFICATION
    # =========================================================================
    story.append(Paragraph("7. Test Cases & Verification Results", style_h1))
    
    test_data = [
        [Paragraph("Test ID", style_table_header), Paragraph("Target Component", style_table_header), Paragraph("Input Condition & Stimulus", style_table_header), Paragraph("Expected Output", style_table_header), Paragraph("Result", style_table_header)],
        [Paragraph("TC-01", style_table_cell), Paragraph("HandDetector", style_table_cell), Paragraph("Blank / Null frame (no hands)", style_table_cell), Paragraph("Empty list returned safely without crash", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-02", style_table_cell), Paragraph("MouseController", style_table_cell), Paragraph("Camera edge coordinate mapping", style_table_cell), Paragraph("Clamped within [0, Screen Width/Height]", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-03", style_table_cell), Paragraph("TremorFilter", style_table_cell), Paragraph("Micro-displacement < 8px", style_table_cell), Paragraph("Position invariant (deadzone activated)", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-04", style_table_cell), Paragraph("GestureClassifier", style_table_cell), Paragraph("Dual-hand: left thumb+index pinch", style_table_cell), Paragraph("Dispatches LEFT_CLICK gesture", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-05", style_table_cell), Paragraph("GestureClassifier", style_table_cell), Paragraph("Dual-hand: left thumb+middle pinch", style_table_cell), Paragraph("Dispatches RIGHT_CLICK gesture", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-06", style_table_cell), Paragraph("GestureClassifier", style_table_cell), Paragraph("Dual-hand: 2 fingers vertical motion", style_table_cell), Paragraph("Dispatches SCROLL_DOWN / SCROLL_UP", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-07", style_table_cell), Paragraph("ClickLock", style_table_cell), Paragraph("Finger shift during click event", style_table_cell), Paragraph("Cursor locked; zero target drift", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)],
        [Paragraph("TC-08", style_table_cell), Paragraph("Visualizer HUD", style_table_cell), Paragraph("Full frame overlay rendering", style_table_cell), Paragraph("Correct BGR shape & skeleton rendering", style_table_cell), Paragraph("<font color='#16a34a'><b>PASSED</b></font>", style_table_cell)]
    ]
    t_test = Table(test_data, colWidths=[0.6 * inch, 1.4 * inch, 2.3 * inch, 2.0 * inch, 0.7 * inch])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_test)
    story.append(Spacer(1, 12))

    # =========================================================================
    # SECTION 8: CONCLUSION & REFERENCES
    # =========================================================================
    story.append(Paragraph("8. Conclusion & Future Scope", style_h1))
    story.append(Paragraph(
        "The <b>AI Virtual Hand Cursor</b> successfully demonstrates an accurate, touch-free replacement for a traditional "
        "hardware mouse. By utilizing MediaPipe's high-fidelity landmark tracking and solving human-computer interaction challenges "
        "(such as click jitter, tremor drift, and dual-hand control isolation), the system provides fluid desktop navigation "
        "across all applications. Automated test coverage validates 100% compliance with all 7 modules outlined in the BCA Mini Project synopsis.<br/><br/>"
        "<b>Future Enhancements:</b><br/>"
        "• Virtual drag-and-drop with pinch-and-hold gestures.<br/>"
        "• Multi-monitor spanning and dynamic monitor switching.<br/>"
        "• Voice command fusion (multimodal speech + gesture controls).",
        style_body
    ))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF Report generated successfully: {filename}")


if __name__ == '__main__':
    build_pdf()
