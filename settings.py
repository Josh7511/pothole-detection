from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CaptureSettings:
    camera_index: int
    interval_sec: float
    image_width: int
    image_height: int
    temp_dir: str
    keep_images_for_debug: bool


@dataclass
class InferenceSettings:
    pothole_class_name: str
    confidence_threshold: float


@dataclass
class GpsSettings:
    enabled: bool
    min_fix_mode: int
    min_satellites: int


@dataclass
class DatabaseSettings:
    path: str
    dedup_distance_m: float


@dataclass
class AlertSettings:
    radius_m: float
    cooldown_sec: float


@dataclass
class NotifierSettings:
    mode: str


@dataclass
class AppSettings:
    model_path: str
    capture: CaptureSettings
    inference: InferenceSettings
    gps: GpsSettings
    database: DatabaseSettings
    alerts: AlertSettings
    notifier: NotifierSettings

    @classmethod
    def load(cls, config_path: str) -> "AppSettings":
        with Path(config_path).open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = yaml.safe_load(handle)

        return cls(
            model_path=raw["model_path"],
            capture=CaptureSettings(**raw["capture"]),
            inference=InferenceSettings(**raw["inference"]),
            gps=GpsSettings(**raw["gps"]),
            database=DatabaseSettings(**raw["database"]),
            alerts=AlertSettings(**raw["alerts"]),
            notifier=NotifierSettings(**raw["notifier"]),
        )
