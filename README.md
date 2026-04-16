# Raspberry Pi Pothole Detector

Edge pothole detection pipeline for Raspberry Pi 5 using Arducam + YOLO classification + NEO-6M GPS.

## Run
1. Install dependencies:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Ensure:
   - YOLO model exists at `models/yolov26n-cls.pt`
   - Camera is connected and readable
   - `gpsd` is running and attached to NEO-6M UART stream
3. Start detector:
   - `python main.py --config config.yaml`

## Quick test run
- `python main.py --config config.yaml --max-iterations 25 --log-level INFO`

## Evaluate logs
- Save runtime output and parse summary metrics:
  - `python scripts/evaluate_log.py runtime.log`

## NEO-6M UART wiring (typical)
- `NEO-6M TX -> Pi RX (GPIO15, pin 10)`
- `NEO-6M RX -> Pi TX (GPIO14, pin 8)`
- `NEO-6M VCC -> 5V or 3.3V (module dependent; verify board)`
- `NEO-6M GND -> Pi GND`

## Notes
- New pothole inserts are deduplicated by distance threshold in config.
- Images are deleted after inference unless debug retention is enabled.
