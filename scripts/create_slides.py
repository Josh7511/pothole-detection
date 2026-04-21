from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt


def add_bullets(prs: Presentation, title: str, bullets: list[str]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    body = slide.shapes.placeholders[1].text_frame
    body.clear()
    for i, bullet in enumerate(bullets):
        p = body.paragraphs[0] if i == 0 else body.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = Pt(24)


def add_code_slide(prs: Presentation, title: str, code_text: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    textbox = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.3), Inches(5.4))
    tf = textbox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = code_text
    p.font.name = "Courier New"
    p.font.size = Pt(14)


def main() -> None:
    prs = Presentation()

    # 1) Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Raspberry Pi Pothole Detection"
    slide.placeholders[1].text = "ELE408 Course Project\nNoah Varghese"

    # 2) Background
    add_bullets(
        prs,
        "Background",
        [
            "Potholes damage vehicles and create safety hazards.",
            "Dashcam road imagery enables visual pothole detection.",
            "Edge computing on Raspberry Pi supports low-latency, offline operation.",
            "Goal: build a practical in-vehicle detector using camera + local alerts.",
        ],
    )

    # 3) Problem Statement
    add_bullets(
        prs,
        "Problem Statement",
        [
            "Detect potholes in real road scenes with an onboard camera.",
            "Store pothole detection events only when confidence is high.",
            "Ignore non-pothole frames to avoid unnecessary storage.",
            "Notify immediately when potholes are detected in real time.",
        ],
    )

    # 4) Basic Idea
    add_bullets(
        prs,
        "Basic Idea",
        [
            "Capture one image every X seconds from Arducam.",
            "Run YOLOv26n-cls inference on Raspberry Pi 5.",
            "If predicted pothole: log event details in SQLite.",
            "Trigger immediate alert and keep GPS extension as future work.",
        ],
    )

    # 5) Implementation
    add_bullets(
        prs,
        "Implementation",
        [
            "Hardware: Raspberry Pi 5 + Arducam 5MP camera.",
            "Software: Python, Ultralytics YOLO, OpenCV, SQLite.",
            "Services: capture, inference, database, notifier.",
            "Main loop coordinates capture -> classify -> log event -> alert.",
        ],
    )

    # 6) Code
    code_text = """# main.py (runtime loop excerpt)
image_path = capture.capture()
prediction = infer.predict(image_path)

if prediction["is_pothole"]:
    db.insert_detection_event(
        detected_at=datetime.now(tz=timezone.utc).isoformat(),
        confidence=float(prediction["confidence"]),
        image_id_optional=image_path.name,
    )
    notifier.notify(
        f"Pothole detected (confidence={float(prediction['confidence']):.2f})"
    )
"""
    add_code_slide(prs, "Code", code_text)

    # 7) Evaluation
    add_bullets(
        prs,
        "Evaluation",
        [
            "Measured metrics: avg inference latency, frames/min, positive events saved.",
            "Log parser script extracts runtime summary from detector logs.",
            "Detector remained stable in repeated runs on Raspberry Pi 5.",
            "Next step: add GPS geotagging and route-based precision/recall.",
        ],
    )

    # 8) Video Documentation
    add_bullets(
        prs,
        "Video Documentation",
        [
            "Demo plan: run detector in moving vehicle with live console output.",
            "Show: image capture cadence, inference labels/confidence, and DB inserts.",
            "Show: immediate alerts triggering for detected potholes.",
            "Insert your final demo link(s) here before presentation.",
        ],
    )

    # 9) References
    add_bullets(
        prs,
        "References",
        [
            "Ultralytics YOLO documentation: https://docs.ultralytics.com",
            "Raspberry Pi documentation: https://www.raspberrypi.com/documentation/",
            "python-pptx project: https://python-pptx.readthedocs.io",
            "Future extension: u-blox NEO-6M integration guides.",
        ],
    )

    output = Path("Pothole_Detection_Presentation.pptx")
    prs.save(output)
    print(f"Created: {output.resolve()}")


if __name__ == "__main__":
    main()
