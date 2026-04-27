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
- Uses `gps.min_satellites: 3` for marginal indoor / window reception (still expect slow or no lock deep indoors).

```bash
python main.py --config config.indoor.yaml --max-iterations 40 --log-level INFO
```

If `gpsd` is not running, the process still runs (camera + inference); you will see `gps_fix=False` until the daemon is up. To skip GPS entirely for a camera-only check, set `gps.enabled` to `false` in the config you use.

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
