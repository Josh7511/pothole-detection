from __future__ import annotations

from pathlib import Path
from time import perf_counter

from ultralytics import YOLO

from settings import InferenceSettings


class InferenceService:
    def __init__(self, model_path: str, settings: InferenceSettings) -> None:
        self._model = YOLO(model_path)
        self._settings = settings

    def predict(self, image_path: Path) -> dict[str, float | str | bool]:
        start = perf_counter()
        result = self._model.predict(source=str(image_path), verbose=False)[0]
        latency_ms = (perf_counter() - start) * 1000.0

        probs = result.probs
        if probs is None:
            return {
                "is_pothole": False,
                "label": "unknown",
                "confidence": 0.0,
                "latency_ms": latency_ms,
            }

        class_id = int(probs.top1)
        confidence = float(probs.top1conf.item())
        label = self._model.names.get(class_id, str(class_id))
        is_pothole = (
            label.lower() == self._settings.pothole_class_name.lower()
            and confidence >= self._settings.confidence_threshold
        )
        return {
            "is_pothole": is_pothole,
            "label": label,
            "confidence": confidence,
            "latency_ms": latency_ms,
        }
