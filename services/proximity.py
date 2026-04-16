from __future__ import annotations

import math
from time import monotonic


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_earth_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius_earth_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class ProximityAlertService:
    def __init__(self, radius_m: float, cooldown_sec: float) -> None:
        self._radius_m = radius_m
        self._cooldown_sec = cooldown_sec
        self._last_alert_monotonic = 0.0

    def should_alert(self, nearest_distance_m: float | None) -> bool:
        if nearest_distance_m is None or nearest_distance_m > self._radius_m:
            return False
        now = monotonic()
        if now - self._last_alert_monotonic < self._cooldown_sec:
            return False
        self._last_alert_monotonic = now
        return True
