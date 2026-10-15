"""SQLite persistence for issued quotes (parameterised queries only)."""
from __future__ import annotations

import sqlite3
import threading
import uuid
from decimal import Decimal


class QuoteStore:
    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("CREATE TABLE IF NOT EXISTS quotes (id TEXT PRIMARY KEY, zone TEXT NOT NULL, "
                             "quantity INTEGER NOT NULL, total TEXT NOT NULL)")
            self._db.commit()

    def save(self, zone: str, quantity: int, total: Decimal) -> str:
        qid = uuid.uuid4().hex
        with self._lock:
            self._db.execute("INSERT INTO quotes (id, zone, quantity, total) VALUES (?, ?, ?, ?)",
                             (qid, zone, quantity, str(total)))
            self._db.commit()
        return qid

    def get(self, qid: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT id, zone, quantity, total FROM quotes WHERE id = ?", (qid,)).fetchone()
        if row is None:
            return None
        return {"id": row[0], "zone": row[1], "quantity": row[2], "total": row[3]}

    def count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM quotes").fetchone()[0])
