"""
core/adapters/process_adapter.py

Process state verifier adapter.
Tracks process PIDs and whether they persist after rollback.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ProcessAdapter:
    """
    Adapter for PROCESS_RUNTIME state domain.
    """

    def hash_state(self, manifest) -> str:
        """Hash process snapshot from manifest."""
        if hasattr(manifest, "process_snapshot"):
            procs = manifest.process_snapshot
        elif isinstance(manifest, dict):
            procs = manifest.get("process_snapshot", [])
        else:
            procs = []

        # Hash the sorted list of process cmd_hashes and PIDs
        summaries = sorted(
            [{"pid": p.get("pid"), "cmd_hash": p.get("cmd_hash", "")}
             for p in procs if "pid" in p],
            key=lambda x: x["pid"],
        )
        payload = json.dumps(summaries, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def get_live_processes(self) -> list[dict]:
        """Get current live process list."""
        procs = []
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    procs.append({
                        "pid": proc.info["pid"],
                        "name": proc.info.get("name", ""),
                        "cmd_hash": hashlib.sha256(
                            " ".join(cmdline).encode()
                        ).hexdigest(),
                    })
                except Exception:
                    pass
        except ImportError:
            pass
        return procs
