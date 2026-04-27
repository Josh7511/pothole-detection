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
        "runId": "post-fix-verify",
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


def _iter_capture_attempts(device_num: int):
    """Pi CSI: rpicam uses libcamera; OpenCV often needs CAP_LIBCAMERA and/or /dev/videoN paths.

    V4L2-by-index alone frequently hits non-capture nodes (see kernel errors on Pi 5).
    """
    dev_path = f"/dev/video{device_num}"
    # Prefer libcamera backend + explicit device path (matches rpicam stack).
    if hasattr(cv2, "CAP_LIBCAMERA"):
        yield "CAP_LIBCAMERA+path", lambda p=dev_path: cv2.VideoCapture(
            p, cv2.CAP_LIBCAMERA
        )
        yield "CAP_LIBCAMERA+index", lambda n=device_num: cv2.VideoCapture(
            n, cv2.CAP_LIBCAMERA
        )
    yield "default+path", lambda p=dev_path: cv2.VideoCapture(p)
    yield "default+index", lambda n=device_num: cv2.VideoCapture(n)
    if hasattr(cv2, "CAP_V4L2"):
        yield "V4L2+path", lambda p=dev_path: cv2.VideoCapture(p, cv2.CAP_V4L2)
        yield "V4L2+index", lambda n=device_num: cv2.VideoCapture(n, cv2.CAP_V4L2)


def _max_opencv_capture_index() -> int:
    """OpenCV VideoCapture(i) uses a small enumerated device list, not /dev/videoN.

    On Raspberry Pi builds, `nb_devices` is often 8 — only indices ``0..7`` are valid
    even when the kernel exposes many more ``/dev/video*`` nodes (ISP, decoder, etc.).
    """
    return 8


def _camera_index_candidates(preferred: int) -> list[int]:
    """Try config index first, then 0..max-1. Never use /dev/videoN as OpenCV index N."""
    cap_max = _max_opencv_capture_index()
    seen: set[int] = set()
    ordered: list[int] = []

    def push(n: int) -> None:
        if 0 <= n < cap_max and n not in seen:
            seen.add(n)
            ordered.append(n)

    if 0 <= preferred < cap_max:
        push(preferred)
    for n in range(cap_max):
        push(n)
    return ordered


def _probe_first_nonempty_frame(cap: cv2.VideoCapture, attempts: int = 25) -> bool:
    for _ in range(attempts):
        ok, fr = cap.read()
        if ok and fr is not None and getattr(fr, "size", 0) > 0:
            return True
        if cap.grab():
            ok_r, fr2 = cap.retrieve()
            if ok_r and fr2 is not None and getattr(fr2, "size", 0) > 0:
                return True
        time.sleep(0.04)
    return False


class CaptureService:
    def __init__(self, settings: CaptureSettings) -> None:
        self._settings = settings
        self._temp_dir = Path(settings.temp_dir)
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        # #region agent log
        index_order = _camera_index_candidates(settings.camera_index)
        _agent_debug_log(
            "H3",
            "capture.py:CaptureService.__init__:entry",
            "Opening camera",
            {
                "camera_index": settings.camera_index,
                "index_try_order": index_order,
                "opencv_index_exclusive_max": _max_opencv_capture_index(),
                "req_w": settings.image_width,
                "req_h": settings.image_height,
                "video_nodes": sorted(
                    str(p) for p in Path("/dev").glob("video*") if p.exists()
                ),
                "opencv_has_CAP_LIBCAMERA": hasattr(cv2, "CAP_LIBCAMERA"),
                "opencv_has_CAP_V4L2": hasattr(cv2, "CAP_V4L2"),
                "opencv_version": getattr(cv2, "__version__", "unknown"),
            },
        )
        # endregion

        res_chain: list[tuple[int, int]] = [
            (settings.image_width, settings.image_height),
        ]
        if res_chain[0] != (640, 480):
            res_chain.append((640, 480))

        self._camera: cv2.VideoCapture | None = None
        chosen: dict[str, str | int | float] = {}
        for idx in index_order:
            for attempt_label, factory in _iter_capture_attempts(idx):
                for rw, rh in res_chain:
                    cap = factory()
                    if not cap.isOpened():
                        cap.release()
                        continue
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, rw)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, rh)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if _probe_first_nonempty_frame(cap):
                        self._camera = cap
                        chosen = {
                            "device_index": idx,
                            "attempt_label": attempt_label,
                            "negotiated_w": rw,
                            "negotiated_h": rh,
                        }
                        break
                    cap.release()
                if self._camera is not None:
                    break
            if self._camera is not None:
                break
            # #region agent log
            _agent_debug_log(
                "H3",
                "capture.py:CaptureService.__init__:index_failed",
                "No frame on this device index",
                {"tried_index": idx},
            )
            # endregion

        if self._camera is None:
            raise RuntimeError(
                "OpenCV could not capture frames (tried libcamera+V4L2 paths and indices "
                f"{index_order}). If `rpicam-hello` works, install OpenCV with libcamera "
                "support or use a libcamera-compatible OpenCV build; confirm no other "
                "process holds the camera."
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
                **chosen,
            },
        )
        _agent_debug_log(
            "FIX",
            "capture.py:CaptureService.__init__:backend_selected",
            "Probe succeeded",
            dict(chosen),
        )
        _agent_debug_log(
            "H4",
            "capture.py:CaptureService.__init__:warmup_done",
            "Warmup skipped; probe already validated nonempty frames",
            {"warmup_first_ok_nonempty": True},
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
