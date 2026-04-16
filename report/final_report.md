# Pothole Detection Final Report

## Project Idea
This project builds an on-device pothole detector on Raspberry Pi 5. The system captures road images from an Arducam 5MP camera every fixed interval, runs a YOLOv26n-cls model locally, and geotags confirmed pothole detections using a u-blox NEO-6M GPS module.

## Hardware and Software
- Raspberry Pi 5
- Arducam 5MP camera
- u-blox NEO-6M breakout (UART)
- Python runtime with Ultralytics YOLO, OpenCV, gpsd-py3, SQLite

## Design and Implementation
The runtime loop performs:
1. Image capture (`services/capture.py`)
2. Classification inference (`services/inference.py`)
3. GPS fix read (`services/gps.py`)
4. Pothole insert into SQLite with duplicate suppression (`services/database.py`)
5. Nearest-pothole distance check and alert (`services/proximity.py`, `services/notify.py`)

The top-level orchestration and metrics logging are implemented in `main.py`.

## Data Storage
Detected potholes are stored in SQLite table `potholes`:
- `id`
- `latitude`
- `longitude`
- `detected_at`
- `confidence`
- `image_id_optional`

## Testing and Results Template
Record the following metrics during field tests:
- Average inference latency (ms/frame)
- Throughput (frames/min)
- GPS fix availability and update rate
- Number of positive detections
- Number of unique potholes stored
- Alert precision while approaching known potholes

## Limitations
- NEO-6M may have slow initial fix and position drift in urban canyons.
- Classifier confidence threshold tuning is route-dependent.
- Single-frame classification can produce false positives/negatives in motion blur conditions.

## Future Work
- Add temporal smoothing over consecutive frames.
- Add audible buzzer and LED hardware notifier.
- Add map visualization of potholes and export tooling.
