#!/usr/bin/env python3
"""
scripts/hooks/posttooluse.py

Rubicon PostToolUse hook.

Called AFTER a tool completes. Cannot block.
Used to capture post-action manifest data and update the ledger.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

_SESSION_ID = os.environ.get("BOB_SESSION_ID", os.environ.get("RUBICON_SESSION_ID", "unknown"))
_POST_ACTION_LOG = _ROOT / "data" / "post_action_events.jsonl"


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    tool_name = data.get("tool_name", data.get("tool", ""))
    tool_output = data.get("tool_output", data.get("output", {}))

    _POST_ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_POST_ACTION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.time(),
            "session_id": _SESSION_ID,
            "tool": tool_name,
            "output_type": type(tool_output).__name__,
        }) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
