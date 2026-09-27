#!/usr/bin/env python3
"""
scripts/hooks/stop.py

Rubicon Stop hook.

Called when the Bob session ends. Cannot block.
Used to finalize session evidence and record session closure.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SESSION_ID = os.environ.get("BOB_SESSION_ID", os.environ.get("RUBICON_SESSION_ID", "unknown"))
_STOP_LOG = _ROOT / "data" / "session_stops.jsonl"


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    _STOP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_STOP_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.time(),
            "session_id": _SESSION_ID,
            "event": "session_stop",
            "data": data,
        }) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
