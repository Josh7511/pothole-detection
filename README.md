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
   - **GPS:** the `gpsd` *package* is installed and the daemon is running (see below)
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

## GPS daemon (`gpsd`) on Raspberry Pi OS
The Python app talks to **`gpsd` over TCP** (port `2947`); a flashing LED on the NEO-6M only means the module is powered.

1. **Install** (if `systemctl` says `gpsd.service` does not exist):
   - `sudo apt update && sudo apt install -y gpsd gpsd-clients`
2. **Point `gpsd` at your UART** (use the stable symlink **`/dev/serial0`** when the NEO-6M is on the Pi’s GPIO UART):
   - Check the mapping: `ls -l /dev/serial*` — on **Raspberry Pi 5** this is often `/dev/serial0 -> ttyAMA10` after serial is enabled in `raspi-config` (Serial port: enable login shell / serial as needed for your OS version).
   - Edit `/etc/default/gpsd` and set `DEVICES="/dev/serial0"` and `GPSD_OPTIONS="-n"`. See `docs/gpsd.default.example` for a full example; copy with `sudo cp` and edit, or merge the lines into the file the package installed.
3. **Restart and enable**:
   - `sudo systemctl restart gpsd` and `sudo systemctl enable gpsd` (or `enable --now gpsd` after install).
4. **Check**:
   - `ss -lntp | grep 2947` should show a listener; `cgps -s` or `gpsmon` should show a fix with sky view.

Use a **stable 5V power supply** for the Pi; undervoltage can make USB/UART flaky (lightning-bolt icon).

## NEO-6M UART wiring (typical)
- `NEO-6M TX -> Pi RX (GPIO15, pin 10)`
- `NEO-6M RX -> Pi TX (GPIO14, pin 8)`
- `NEO-6M VCC -> 5V or 3.3V (module dependent; verify board)`
- `NEO-6M GND -> Pi GND`

## Notes
- New pothole inserts are deduplicated by distance threshold in config.
- Images are deleted from `capture.temp_dir` after each cycle unless `keep_images_for_debug` is true. Positive pothole frames are also copied to **`capture.positive_detections_dir`** when that path is set (JPEG files only; the database still stores coordinates and optional filename, not image bytes).
