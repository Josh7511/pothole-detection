# Pothole Detection Final Report

## Background
Rhode Island is frequently cited among the states with the worst road conditions in the country, with rough pavement and recurring potholes creating daily frustration for drivers. These road issues are more than an inconvenience: they can damage vehicles, increase maintenance costs, and create safety risks for motorists, cyclists, and emergency responders.

At the same time, low-cost embedded platforms such as Raspberry Pi have made it easier to build practical sensing systems outside of traditional infrastructure programs. Instead of relying only on slow manual surveys, communities can use compact computer-vision tools to observe road quality continuously. This project is motivated by that need: a simple, affordable system that can detect potholes during normal driving and produce useful location data for road maintenance decisions.

## Problem Statement
Road potholes cause vehicle damage and safety risks, but manual inspection is slow and expensive. This project aims to automatically detect potholes during regular driving, record their locations, and make these records available for maintenance planning.

## Basic Idea
The system captures road images from an Arducam 5MP camera every fixed interval, runs a YOLOv26n-cls model locally on Raspberry Pi 5, and logs high-confidence pothole detection events for later review.

## System Architecture Design
The runtime loop performs:
1. Image capture (`services/capture.py`)
2. Classification inference (`services/inference.py`)
3. Pothole event insert into SQLite (`services/database.py`)
4. Immediate user notification on pothole detections (`services/notify.py`)
5. Optional GPS and proximity logic retained for future extension (`services/gps.py`, `services/proximity.py`)

The top-level orchestration and metrics logging are implemented in `main.py`.

## Implementation
The system was assembled based on the architecture design by connecting the Arducam to the Raspberry Pi camera interface and deploying the Python runtime on-device. A timed main loop was created in `main.py` to repeatedly capture frames, run classification with Ultralytics YOLO, and decide whether a detection should be saved.

To keep performance usable on-device, image preprocessing and inference calls were kept lightweight, and confidence threshold filtering was applied before writing records. A SQLite database layer (`services/database.py`) was implemented with a `detection_events` table so each confirmed detection is saved with detection time, confidence score, and an optional image reference. For demo reliability, the runtime uses immediate notifications on positive detections and deletes non-debug images after inference to limit storage growth.

## Evaluation
Testing showed that the complete capture and inference pipeline worked reliably on Raspberry Pi 5. The camera capture and inference loop remained stable for extended runs, and the model was generally able to identify larger potholes and rough patches with moderate-to-high confidence. During controlled testing sessions, the system logged repeated positive events near visibly damaged road segments, showing that event logging and real-time notification were functioning as intended.

Some inconsistent behavior was observed in challenging conditions. Rapid vehicle motion, heavy shadows, and uneven lighting occasionally caused missed detections or false positives, especially for shallow potholes. While the current implementation does not fully eliminate false detections, the overall results demonstrate a practical edge-computing foundation that can be improved with additional training data, temporal smoothing, and full GPS integration in future work.
