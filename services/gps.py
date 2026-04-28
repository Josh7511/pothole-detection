from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gpsd

from settings import GpsSettings


# #region agent log
def _agent_gps_debug(
    hypothesis_id: str, location: str, message: str, data: dict
) -> None:
    root = Path(__file__).resolve().parent.parent
    payload = {
        "sessionId": "caef2d",
        "runId": "car-gps",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload)
    for log_path in (root / ".cursor" / "debug-caef2d.log", root / "debug-caef2d.log"):
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


# endregion


@dataclass
class GpsFix:
    latitude: float
    longitude: float
    timestamp: str
    mode: int
    satellites: int


class GpsService:
    def __init__(self, settings: GpsSettings) -> None:
        self._settings = settings
        self._connected = False
        if not settings.enabled:
            return
        if settings.use_mock_fix:
            logging.info(
                "GPS mock fix enabled at (%.6f, %.6f); gpsd is not used. "
                "Turn off gps.use_mock_fix for live GNSS.",
                settings.mock_latitude,
                settings.mock_longitude,
            )
            return
        try:
            gpsd.connect()
            self._connected = True
            # #region agent log
            _agent_gps_debug(
                "H1",
                "gps.py:GpsService.__init__:connect_ok",
                "gpsd.connect succeeded",
                {"default_endpoint": "127.0.0.1:2947 (typical for gpsd-py3)"},
            )
            # endregion
        except Exception as exc:
            en = getattr(exc, "errno", None)
            is_refused = type(exc).__name__ == "ConnectionRefusedError" or en == 111
            # #region agent log
            _agent_gps_debug(
                "H1",
                "gps.py:GpsService.__init__:connect_fail",
                "gpsd.connect failed",
                {
                    "exc_type": type(exc).__name__,
                    "errno": en,
                    "suggests_gpsd_not_listening": is_refused,
                },
            )
            # endregion
            extra = ""
            if is_refused:
                extra = (
                    "Connection refused means the gpsd *daemon* is not accepting TCP (nothing on port 2947). "
                    "The GPS LED only shows the module has power; you still need: "
                    "`sudo systemctl start gpsd` (or `sudo systemctl enable --now gpsd`), "
                    "and `DEVICES=\"/dev/serial0\"` (or your UART) in `/etc/default/gpsd` on Pi OS, then `sudo systemctl restart gpsd`. "
                )
            tail = (
                "On the Pi, verify: `ss -lntp | grep 2947` (should show gpsd), and `cgps -s` with a sky view. "
                "Or set gps.use_mock_fix: true (bench) / gps.enabled: false (camera-only)."
            )
            logging.warning(
                "GPS enabled but gpsd is unreachable (%s); running without fixes. %s %s",
                type(exc).__name__,
                extra,
                tail,
            )

    def get_fix(self) -> GpsFix | None:
        if not self._settings.enabled:
            return None
        if self._settings.use_mock_fix:
            return GpsFix(
                latitude=float(self._settings.mock_latitude),
                longitude=float(self._settings.mock_longitude),
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
                mode=3,
                satellites=12,
            )
        if not self._connected:
            return None
        try:
            packet: Any = gpsd.get_current()
        except Exception:
            return None

        mode = int(getattr(packet, "mode", 0) or 0)
        satellites = int(getattr(packet, "sats", 0) or 0)
        if mode < self._settings.min_fix_mode:
            return None
        if satellites < self._settings.min_satellites:
            return None

        lat = getattr(packet, "lat", None)
        lon = getattr(packet, "lon", None)
        if lat is None or lon is None:
            return None

        return GpsFix(
            latitude=float(lat),
            longitude=float(lon),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            mode=mode,
            satellites=satellites,
        )
