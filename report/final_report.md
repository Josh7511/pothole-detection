# Pothole Detection Final Report

## Background
Rhode Island is frequently cited among the states with the worst road conditions in the country, with rough pavement and recurring potholes creating daily frustration for drivers. These road issues are more than an inconvenience: they can damage vehicles, increase maintenance costs, and create safety risks for motorists, cyclists, and emergency responders.

At the same time, low-cost embedded platforms such as Raspberry Pi have made it easier to build practical sensing systems outside of traditional infrastructure programs. Instead of relying only on slow manual surveys, communities can use compact computer-vision tools to observe road quality continuously. This project is motivated by that need: a simple, affordable system that can detect potholes during normal driving and produce useful location data for road maintenance decisions.

## Problem Statement
Road potholes cause vehicle damage and safety risks, but manual inspection is slow and expensive. This project aims to automatically detect potholes during regular driving, record their locations, and make these records available for maintenance planning.

## Basic Idea
The system captures road images from an Arducam 5MP camera every fixed interval, runs a YOLOv26n-cls model locally on Raspberry Pi 5, and geotags confirmed pothole detections using a u-blox NEO-6M GPS module.

## System Architecture Design
The runtime loop performs:
1. Image capture (`services/capture.py`)
2. Classification inference (`services/inference.py`)
3. GPS fix read (`services/gps.py`)
4. Pothole insert into SQLite with duplicate suppression (`services/database.py`)
5. Nearest-pothole distance check and alert (`services/proximity.py`, `services/notify.py`)

The top-level orchestration and metrics logging are implemented in `main.py`.

## Implementation
The system was assembled based on the architecture design, connecting the Arducam to the Raspberry Pi camera interface and the NEO-6M GPS module through UART. After hardware setup, the Python runtime was implemented on the Raspberry Pi to coordinate sensor input, model inference, and data logging. A timed main loop was created in `main.py` to repeatedly capture frames, run classification with Ultralytics YOLO, query GPS coordinates, and decide whether a detection should be saved.

To keep performance usable on-device, image preprocessing and inference calls were kept lightweight, and confidence threshold filtering was applied before writing records. A SQLite database layer (`services/database.py`) was implemented with a `potholes` table so each confirmed detection is saved with latitude, longitude, detection time, confidence score, and an optional image reference. The same database is also queried during runtime for duplicate suppression, preventing repeated inserts of the same road defect across nearby frames, and for proximity checks against previously logged potholes. Finally, proximity logic was implemented to compare the current GPS position against stored records and trigger user notifications when the vehicle approached a known damaged segment.

## Evaluation
Field testing showed that the complete detection pipeline worked reliably during regular driving. The camera capture and inference loop remained stable for extended runs, and the model was generally able to identify larger potholes and rough patches with moderate-to-high confidence. In several test drives around Pawtucket and nearby streets, the system logged repeated detections near the same damaged road segments, which indicates that the GPS tagging and duplicate suppression logic were functioning as intended.

Some inconsistent behavior was observed in challenging conditions. Rapid vehicle motion, heavy shadows, and uneven lighting occasionally caused missed detections or false positives, especially for shallow potholes. GPS accuracy also varied by location, with slight coordinate drift near dense buildings. Even with these issues, the system still produced a useful map of frequently damaged roadway areas and successfully triggered proximity alerts when approaching previously stored pothole locations. While the current implementation does not fully eliminate false detections, the overall results demonstrate a practical foundation that can be improved with additional training data and temporal smoothing.
