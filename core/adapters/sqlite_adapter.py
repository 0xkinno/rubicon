"""
core/adapters/sqlite_adapter.py

SQLite database state verifier adapter.
Uses a disposable local SQLite fixture — no client/company data.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


class SQLiteAdapter:
    """
    Adapter for DATABASE_STATE domain.
    Uses a local SQLite fixture to demonstrate database is a distinct state domain.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def hash_state(self, manifest=None) -> str:
        """
        Hash the current database state independently.
        If manifest is provided, we use the manifest's timestamp to decide
        but we always re-read from the actual database file.
        """
        return self._hash_db_file()

    def _hash_db_file(self) -> str:
        """Hash the raw SQLite file bytes."""
        try:
            return hashlib.sha256(self._db_path.read_bytes()).hexdigest()
        except FileNotFoundError:
            return "FILE_NOT_FOUND"
        except OSError as exc:
            return f"ERROR:{hashlib.sha256(str(exc).encode()).hexdigest()[:12]}"

    def get_table_hashes(self) -> dict[str, str]:
        """Hash each table's content for fine-grained comparison."""
        hashes = {}
        if not self._db_path.exists():
            return hashes
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                rows = cursor.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                payload = json.dumps(rows, default=str)
                hashes[table] = hashlib.sha256(payload.encode()).hexdigest()
            conn.close()
        except Exception as exc:
            hashes["error"] = str(exc)
        return hashes

    def initialize_fixture(self) -> None:
        """Create the demo SQLite fixture table if it doesn't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rubicon_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def insert_event(self, event_type: str, payload: dict) -> int:
        """Insert a test event record."""
        import time
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.execute(
            "INSERT INTO rubicon_events (event_type, payload, created_at) VALUES (?, ?, ?)",
            (event_type, json.dumps(payload), time.time()),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id
