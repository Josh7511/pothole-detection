from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import gpsd

from settings import GpsSettings


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
        except Exception as exc:
            logging.warning(
                "GPS enabled but gpsd is unreachable (%s); running without fixes. "
                "Start gpsd on your serial device (e.g. `sudo gpsd /dev/serial0 -F /var/run/gpsd.sock`), "
                "verify with `cgps -s`, or set gps.use_mock_fix: true for indoor bench, "
                "or gps.enabled: false for camera-only.",
                type(exc).__name__,
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
