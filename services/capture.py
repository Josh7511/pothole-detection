from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from settings import CaptureSettings


class CaptureService:
    def __init__(self, settings: CaptureSettings) -> None:
        self._settings = settings
        self._temp_dir = Path(settings.temp_dir)
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._camera = cv2.VideoCapture(settings.camera_index)
        self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.image_width)
        self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.image_height)
        if not self._camera.isOpened():
            raise RuntimeError(
                f"Could not open camera index {settings.camera_index}. "
                "Verify Arducam and camera permissions."
            )
        # Many USB/CSI modules on Pi return no frame on the first read() after open.
        for _ in range(15):
            ok, _ = self._camera.read()
            if ok:
                break
            time.sleep(0.05)

    def capture(self) -> Path:
        frame = None
        for _ in range(30):
            ok, frame = self._camera.read()
            if ok and frame is not None and getattr(frame, "size", 0) > 0:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("Camera read failed.")

        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        image_path = self._temp_dir / f"{stamp}.jpg"
        cv2.imwrite(str(image_path), frame)
        return image_path

    def cleanup_image(self, image_path: Path) -> None:
        if self._settings.keep_images_for_debug:
            return
        if image_path.exists():
            image_path.unlink()

    def close(self) -> None:
        self._camera.release()
