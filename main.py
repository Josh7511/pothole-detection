from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
import time
from dataclasses import dataclass

from settings import AppSettings
from services.capture import CaptureService
from services.database import DatabaseService
from services.gps import GpsFix, GpsService
from services.inference import InferenceService
from services.notify import NotifierService
from services.proximity import ProximityAlertService


@dataclass
class RuntimeStats:
    total_frames: int = 0
    positive_frames: int = 0
    gps_fixes_used: int = 0
    potholes_saved: int = 0
    events_saved: int = 0
    total_inference_ms: float = 0.0

    def report(self, elapsed_sec: float) -> str:
        avg_ms = self.total_inference_ms / self.total_frames if self.total_frames else 0.0
        fpm = (self.total_frames / elapsed_sec * 60.0) if elapsed_sec > 0 else 0.0
        return (
            f"frames={self.total_frames}, positives={self.positive_frames}, "
            f"saved={self.potholes_saved}, events={self.events_saved}, "
            f"gps_fixes={self.gps_fixes_used}, "
            f"avg_inference_ms={avg_ms:.1f}, throughput_fpm={fpm:.1f}"
        )


def run(config_path: str, max_iterations: int | None) -> None:
    settings = AppSettings.load(config_path)

    capture = CaptureService(settings.capture)
    infer = InferenceService(settings.model_path, settings.inference)
    gps = GpsService(settings.gps)
    db = DatabaseService(settings.database)
    proximity = ProximityAlertService(settings.alerts.radius_m, settings.alerts.cooldown_sec)
    notifier = NotifierService(settings.notifier.mode)
    stats = RuntimeStats()
    start = time.monotonic()

    try:
        i = 0
        while max_iterations is None or i < max_iterations:
            cycle_start = time.monotonic()
            i += 1

            image_path = capture.capture()
            fix: GpsFix | None = gps.get_fix()
            prediction = infer.predict(image_path)
            stats.total_frames += 1
            stats.total_inference_ms += float(prediction["latency_ms"])

            is_pothole = bool(prediction["is_pothole"])
            confidence = float(prediction["confidence"])
            label = str(prediction["label"])

            if is_pothole:
                stats.positive_frames += 1
                db.insert_detection_event(
                    detected_at=datetime.now(tz=timezone.utc).isoformat(),
                    confidence=confidence,
                    image_id_optional=image_path.name,
                )
                stats.events_saved += 1
                if fix is not None:
                    stats.gps_fixes_used += 1
                    inserted = db.insert_pothole(
                        latitude=fix.latitude,
                        longitude=fix.longitude,
                        detected_at=fix.timestamp,
                        confidence=confidence,
                        image_id_optional=image_path.name,
                    )
                    if inserted:
                        stats.potholes_saved += 1
                else:
                    notifier.notify(f"Pothole detected (confidence={confidence:.2f}).")

            if fix is not None:
                nearest = db.nearest_distance_m(fix.latitude, fix.longitude)
                if proximity.should_alert(nearest):
                    notifier.notify(f"Pothole ahead in {nearest:.1f} meters.")

            logging.info(
                "frame=%s label=%s conf=%.3f pothole=%s gps_fix=%s",
                image_path.name,
                label,
                confidence,
                is_pothole,
                fix is not None,
            )
            capture.cleanup_image(image_path)

            elapsed = time.monotonic() - cycle_start
            to_sleep = max(0.0, settings.capture.interval_sec - elapsed)
            time.sleep(to_sleep)
    except KeyboardInterrupt:
        logging.info("Shutting down after keyboard interrupt.")
    finally:
        capture.close()
        db.close()
        run_elapsed = time.monotonic() - start
        logging.info("Runtime summary: %s", stats.report(run_elapsed))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raspberry Pi pothole detector runtime.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file.")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Optional frame count limit for test runs.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Runtime logging level.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")
    run(config_path=args.config, max_iterations=args.max_iterations)
