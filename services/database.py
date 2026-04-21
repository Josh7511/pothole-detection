from __future__ import annotations

import sqlite3
from pathlib import Path

from settings import DatabaseSettings

from .proximity import haversine_distance_m


class DatabaseService:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        db_path = Path(settings.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS potholes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                detected_at TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_id_optional TEXT
            )
            """
        )
        self._conn.commit()

    def _is_duplicate(self, latitude: float, longitude: float) -> bool:
        rows = self._conn.execute(
            "SELECT latitude, longitude FROM potholes ORDER BY id DESC LIMIT 100"
        ).fetchall()
        for row in rows:
            existing_lat, existing_lon = float(row[0]), float(row[1])
            if (
                haversine_distance_m(latitude, longitude, existing_lat, existing_lon)
                <= self._settings.dedup_distance_m
            ):
                return True
        return False

    def insert_pothole(
        self,
        latitude: float,
        longitude: float,
        detected_at: str,
        confidence: float,
        image_id_optional: str | None = None,
    ) -> bool:
        if self._is_duplicate(latitude, longitude):
            return False
        self._conn.execute(
            """
            INSERT INTO potholes(latitude, longitude, detected_at, confidence, image_id_optional)
            VALUES (?, ?, ?, ?, ?)
            """,
            (latitude, longitude, detected_at, confidence, image_id_optional),
        )
        self._conn.commit()
        return True

    def nearest_distance_m(self, latitude: float, longitude: float) -> float | None:
        rows = self._conn.execute("SELECT latitude, longitude FROM potholes").fetchall()
        if not rows:
            return None
        distances = [
            haversine_distance_m(latitude, longitude, float(row[0]), float(row[1]))
            for row in rows
        ]
        return min(distances)

    def close(self) -> None:
        self._conn.close()
