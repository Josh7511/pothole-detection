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
        if settings.enabled:
            try:
                gpsd.connect()
                self._connected = True
            except Exception:
                logging.warning(
                    "GPS enabled but gpsd is unreachable; running without fixes. "
                    "Start gpsd or set gps.enabled to false in config."
                )

    def get_fix(self) -> GpsFix | None:
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
