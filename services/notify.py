from __future__ import annotations

from datetime import datetime


class NotifierService:
    def __init__(self, mode: str = "console") -> None:
        self._mode = mode

    def notify(self, message: str) -> None:
        if self._mode == "console":
            print(f"[ALERT {datetime.now().isoformat(timespec='seconds')}] {message}")
