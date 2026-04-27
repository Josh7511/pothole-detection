# Raspberry Pi Pothole Detector

Edge pothole detection pipeline for Raspberry Pi 5 using Arducam + YOLO classification + NEO-6M GPS.

## Run
1. Install dependencies:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Ensure:
   - YOLO weights exist at `models/best.pt` (or set `model_path` in your config)
   - Camera is connected and readable
   - `gpsd` is running and attached to NEO-6M UART stream
3. Start detector:
   - `python main.py --config config.yaml`

## Quick test run
- `python main.py --config config.yaml --max-iterations 25 --log-level INFO`

## Indoor / bench test
Use `config.indoor.yaml` on a desk before mounting in a vehicle:
- Keeps JPEGs under `capture.temp_dir` so you can verify the camera.
- Writes detections to `data/indoor_test.db` instead of your main database.
- **`gps.use_mock_fix: true`** returns a synthetic fix (`mock_latitude` / `mock_longitude`) so DB inserts work without `gpsd` or sky view. Set **`use_mock_fix: false`**, run **`gpsd`**, and optionally lower **`min_satellites`** (e.g. `3`) for real weak-indoor GNSS.

```bash
python main.py --config config.indoor.yaml --max-iterations 40 --log-level INFO
```

For production / vehicle runs, use **`config.yaml`** with **`use_mock_fix: false`** (or omit mock keys). For camera-only, set **`gps.enabled`** to **`false`**.

On Raspberry Pi, the camera path **skips OpenCV’s V4L2 scan by default** and uses **`rpicam-still` with `--zsl`** so the ISP stack is not left busy (`/dev/video*` EBUSY). To force the old behavior (try OpenCV indices first), set **`POTHOLE_TRY_OPENCV_CAMERA=1`**. To force skipping OpenCV on non-Pi machines, use **`POTHOLE_SKIP_OPENCV_CAMERA=1`**.

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
- Images are deleted from `capture.temp_dir` after each cycle unless `keep_images_for_debug` is true. Positive pothole frames are also copied to **`capture.positive_detections_dir`** when that path is set (JPEG files only; the database still stores coordinates and optional filename, not image bytes).
