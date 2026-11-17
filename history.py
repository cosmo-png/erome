"""SQLite record of finished albums, so reruns only grab new ones."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .config import home_dir


class History:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else home_dir() / "history.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS albums ("
            "id TEXT PRIMARY KEY, title TEXT, url TEXT, files INTEGER, saved_at REAL)"
        )
        self._db.commit()

    def done_ids(self) -> set[str]:
        with self._lock:
            return {row[0] for row in self._db.execute("SELECT id FROM albums")}

    def mark(self, album_id: str, title: str, url: str, files: int) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO albums VALUES (?, ?, ?, ?, ?)",
                (album_id, title, url, files, time.time()),
            )
            self._db.commit()

    def close(self) -> None:
        self._db.close()
