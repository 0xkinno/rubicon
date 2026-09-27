"""
core/adapters/http_fixture_adapter.py

External HTTP fixture adapter.
Runs a disposable local HTTP service with an append-only event endpoint.
Demonstrates that POST effects persist even after workspace rollback.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Append-only event store (in-memory + file)
# ─────────────────────────────────────────────────────────────────────────────

class EventStore:
    def __init__(self, events_file: Path) -> None:
        self._file = events_file
        self._lock = threading.Lock()
        self._file.parent.mkdir(parents=True, exist_ok=True)
        if not self._file.exists():
            self._file.write_text("", encoding="utf-8")

    def append(self, event: dict) -> None:
        with self._lock:
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

    def read_all(self) -> list[dict]:
        with self._lock:
            lines = self._file.read_text(encoding="utf-8").splitlines()
        events = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return events

    def hash(self) -> str:
        events = self.read_all()
        payload = json.dumps(events, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP handler
# ─────────────────────────────────────────────────────────────────────────────

_store: Optional[EventStore] = None


class _Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == "/events":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            try:
                event = json.loads(body) if body else {}
            except json.JSONDecodeError:
                event = {"raw": body.decode(errors="replace")}
            event["server_ts"] = time.time()
            if _store:
                _store.append(event)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/events" and _store:
            events = _store.read_all()
            body = json.dumps(events, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/hash" and _store:
            body = json.dumps({"hash": _store.hash()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # Silence default access log


# ─────────────────────────────────────────────────────────────────────────────
# HTTP fixture adapter
# ─────────────────────────────────────────────────────────────────────────────

class HTTPFixtureAdapter:
    """
    Adapter for EXTERNAL_NETWORK state domain.

    Spins up a local disposable event receiver on a free port.
    Captures the event log hash before/after agent actions.
    """

    def __init__(self, events_file: Path, host: str = "127.0.0.1", port: int = 9876) -> None:
        global _store
        self._events_file = events_file
        self._store = EventStore(events_file)
        _store = self._store
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        """Start the fixture server. Returns base URL."""
        self._server = HTTPServer((self._host, self._port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://{self._host}:{self._port}"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

    def hash_state(self, manifest=None) -> str:
        """Return the current event log hash (independent of Bob's workspace)."""
        return self._store.hash()

    def get_event_count(self) -> int:
        return len(self._store.read_all())

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"
