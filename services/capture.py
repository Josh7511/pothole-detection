from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from settings import CaptureSettings


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


def _opencv_skip_state() -> tuple[bool, str]:
    """(skip OpenCV loop, reason). On Raspberry Pi, default skip — V4L2 probing leaves /dev/video* busy (log evidence)."""
    env_try = os.environ.get("POTHOLE_TRY_OPENCV_CAMERA", "").strip().lower()
    if env_try in ("1", "true", "yes"):
        return False, "try_opencv_env"
    env_skip = os.environ.get("POTHOLE_SKIP_OPENCV_CAMERA", "").strip().lower()
    if env_skip in ("1", "true", "yes"):
        return True, "skip_opencv_env"
    try:
        model = Path("/proc/device-tree/model").read_bytes().decode(
            "ascii", errors="ignore"
        )
        if "raspberry pi" in model.lower():
            return True, "default_raspberry_pi"
    except OSError:
        pass
    return False, "default_non_pi"


def _rpicam_stderr_retryable(stderr: str) -> bool:
    s = stderr.lower()
    return any(
        needle in s
        for needle in (
            "device or resource busy",
            "resource busy",
            "could not allocate",
            "failed to allocate",
            "unable to acquire",
            "camera is in use",
        )
    )


def _find_rpicam_still() -> str | None:
    for cand in (
        shutil.which("rpicam-still"),
        shutil.which("libcamera-still"),
        "/usr/bin/rpicam-still",
        "/usr/bin/libcamera-still",
    ):
        if cand and Path(cand).is_file() and os.access(cand, os.X_OK):
            return cand
    return None


def _probe_jpeg_readable(path: Path) -> bool:
    if not path.exists():
        return False
    sz = path.stat().st_size
    if sz < 500:
        return False
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    ok = img is not None and getattr(img, "size", 0) > 0
    if ok:
        return True
    return sz >= 5000


def _probe_rpicam_still(
    settings: CaptureSettings, _temp_dir: Path
) -> tuple[str | None, str]:
    """Return (exe, dim_style). Probe under /tmp; retry when libcamera reports busy."""
    exe = _find_rpicam_still()
    if not exe:
        return None, "minimal"
    probe_path = Path("/tmp/_pothole_probe_rpicam_still.jpg")
    w, h = settings.image_width, settings.image_height
    # --zsl: Pi 5 ISP often fails with EBUSY on /dev/video4 without it (see libcamera stderr).
    attempts: list[tuple[str, list[str]]] = [
        (
            "minimal",
            [exe, "--zsl", "-t", "200", "--nopreview", "-o", str(probe_path)],
        ),
        (
            "explicit_wh",
            [
                exe,
                "--zsl",
                "-t",
                "200",
                "--nopreview",
                "-o",
                str(probe_path),
                "--width",
                str(w),
                "--height",
                str(h),
            ],
        ),
    ]
    max_retries = 8
    for dim_style, cmd in attempts:
        for retry in range(max_retries):
            if probe_path.exists():
                try:
                    probe_path.unlink()
                except OSError:
                    pass
            proc: subprocess.CompletedProcess[str] | None = None
            try:
                proc = subprocess.run(
                    cmd,
                    check=False,
                    timeout=45,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL,
                    env=os.environ,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                break
            stderr = (proc.stderr or "") if proc else ""
            if proc and proc.returncode == 0 and _probe_jpeg_readable(probe_path):
                try:
                    probe_path.unlink()
                except OSError:
                    pass
                return exe, dim_style
            if (
                retry < max_retries - 1
                and proc is not None
                and _rpicam_stderr_retryable(stderr)
            ):
                delay = min(12.0, 2.0 + retry * 1.5)
                time.sleep(delay)
                continue
            break
    return None, "minimal"


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
        self._rpicam_mode = False
        self._rpicam_exe: str | None = None
        self._rpicam_dim_style: str = "minimal"
        skip_opencv, skip_opencv_reason = _opencv_skip_state()
        index_order = _camera_index_candidates(settings.camera_index)

        self._camera: cv2.VideoCapture | None = None

        if not skip_opencv:
            res_chain: list[tuple[int, int]] = [
                (settings.image_width, settings.image_height),
            ]
            if res_chain[0] != (640, 480):
                res_chain.append((640, 480))

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
                            break
                        cap.release()
                    if self._camera is not None:
                        break
                if self._camera is not None:
                    break

        if self._camera is None:
            # OpenCV probing can leave the CSI stack busy; wait before libcamera CLI.
            if not skip_opencv:
                time.sleep(3.0)
            self._rpicam_exe, self._rpicam_dim_style = _probe_rpicam_still(
                settings, self._temp_dir
            )
            if self._rpicam_exe:
                self._rpicam_mode = True
            else:
                hint = (
                    "On Pi, OpenCV probing is skipped by default (README). "
                    "Close other camera apps and retry. "
                    "Set POTHOLE_TRY_OPENCV_CAMERA=1 only if you need the V4L2 scan."
                )
                raise RuntimeError(
                    "Could not capture frames "
                    + (
                        f"(OpenCV skipped: {skip_opencv_reason}) "
                        if skip_opencv
                        else f"(OpenCV tried indices {index_order}) "
                    )
                    + "and rpicam-still (--zsl) probe failed after retries. "
                    + hint
                    + " Ensure `rpicam-still` works alone and nothing else uses the camera."
                )

    def capture(self) -> Path:
        if self._rpicam_mode and self._rpicam_exe:
            return self._capture_rpicam_still()

        frame = None
        attempts_used = 0
        for attempts_used in range(30):
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

    def _capture_rpicam_still(self) -> Path:
        assert self._rpicam_exe is not None
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        image_path = self._temp_dir / f"{stamp}.jpg"
        w, h = self._settings.image_width, self._settings.image_height
        cmd = [
            self._rpicam_exe,
            "--zsl",
            "-t",
            "200",
            "--nopreview",
            "-o",
            str(image_path),
        ]
        if self._rpicam_dim_style == "explicit_wh":
            cmd.extend(["--width", str(w), "--height", str(h)])
        max_retries = 8
        proc: subprocess.CompletedProcess[str] | None = None
        for retry in range(max_retries):
            proc = subprocess.run(
                cmd,
                check=False,
                timeout=45,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                env=os.environ,
            )
            stderr = proc.stderr or ""
            if proc.returncode == 0:
                break
            if retry < max_retries - 1 and _rpicam_stderr_retryable(stderr):
                time.sleep(min(12.0, 2.0 + retry * 1.5))
                continue
            raise RuntimeError(
                f"rpicam-still failed (code {proc.returncode}): {stderr[-1200:]!s}"
            )
        if proc is None or proc.returncode != 0:
            raise RuntimeError("rpicam-still failed with no capture path.")
        img = cv2.imread(str(image_path))
        if img is None or getattr(img, "size", 0) == 0:
            raise RuntimeError("rpicam-still did not produce a readable image.")
        return image_path

    def cleanup_image(self, image_path: Path) -> None:
        if self._settings.keep_images_for_debug:
            return
        if image_path.exists():
            image_path.unlink()

    def close(self) -> None:
        if self._camera is not None:
            self._camera.release()
