from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from settings import CaptureSettings

# region agent log
def _agent_debug_log(
    hypothesis_id: str, location: str, message: str, data: dict
) -> None:
    root = Path(__file__).resolve().parent.parent
    payload = {
        "sessionId": "caef2d",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload)
    # Always mirror to stderr so bench runs produce evidence even if file paths differ.
    print(f"AGENT_DEBUG_JSON {line}", file=sys.stderr, flush=True)
    for log_path in (root / ".cursor" / "debug-caef2d.log", root / "debug-caef2d.log"):
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as exc:
            print(f"AGENT_DEBUG_LOG_WRITE_FAIL {log_path}: {exc}", file=sys.stderr, flush=True)


# endregion


class CaptureService:
    def __init__(self, settings: CaptureSettings) -> None:
        self._settings = settings
        self._temp_dir = Path(settings.temp_dir)
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        # #region agent log
        _agent_debug_log(
            "H3",
            "capture.py:CaptureService.__init__:entry",
            "Opening camera",
            {
                "camera_index": settings.camera_index,
                "req_w": settings.image_width,
                "req_h": settings.image_height,
                "video_nodes": sorted(
                    str(p) for p in Path("/dev").glob("video*") if p.exists()
                ),
            },
        )
        # endregion
        self._camera = cv2.VideoCapture(settings.camera_index)
        self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.image_width)
        self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.image_height)
        if not self._camera.isOpened():
            raise RuntimeError(
                f"Could not open camera index {settings.camera_index}. "
                "Verify Arducam and camera permissions."
            )
        # #region agent log
        try:
            backend_name = self._camera.getBackendName()
        except Exception:
            backend_name = "unknown"
        actual_w = self._camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        _agent_debug_log(
            "H1",
            "capture.py:CaptureService.__init__:after_open",
            "Capture opened",
            {
                "backend_name": backend_name,
                "is_opened": self._camera.isOpened(),
                "actual_w": actual_w,
                "actual_h": actual_h,
            },
        )
        # endregion
        # Many USB/CSI modules on Pi return no frame on the first read() after open.
        warmup_first_ok_nonempty: bool | None = None
        for _ in range(15):
            ok, fr = self._camera.read()
            if ok:
                warmup_first_ok_nonempty = bool(
                    fr is not None and getattr(fr, "size", 0) > 0
                )
                break
            time.sleep(0.05)
        # #region agent log
        _agent_debug_log(
            "H4",
            "capture.py:CaptureService.__init__:warmup_done",
            "Warmup summary (original break on ok only)",
            {"warmup_first_ok_nonempty": warmup_first_ok_nonempty},
        )
        # endregion

    def capture(self) -> Path:
        frame = None
        last_ok = False
        last_size = 0
        attempts_used = 0
        for attempts_used in range(30):
            ok, frame = self._camera.read()
            last_ok = bool(ok)
            last_size = int(getattr(frame, "size", 0) or 0) if frame is not None else 0
            if ok and frame is not None and getattr(frame, "size", 0) > 0:
                break
            time.sleep(0.05)
        else:
            # #region agent log
            _agent_debug_log(
                "H5",
                "capture.py:CaptureService.capture:failed",
                "All read attempts failed",
                {
                    "attempts": attempts_used + 1,
                    "last_ok": last_ok,
                    "last_frame_size": last_size,
                    "still_opened": self._camera.isOpened(),
                },
            )
            # endregion
            raise RuntimeError("Camera read failed.")
        # #region agent log
        _agent_debug_log(
            "H2",
            "capture.py:CaptureService.capture:ok",
            "Frame captured",
            {
                "attempts_used": attempts_used + 1,
                "shape": list(frame.shape) if frame is not None else None,
            },
        )
        # endregion

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
