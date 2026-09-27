#!/usr/bin/env python3
"""
scripts/discovery/run_experiments.py

Phase 0 discovery experiments R01–R12.
Run against the real Bob instance to characterize rollback behavior.

IMPORTANT: These scripts observe and record behavior.
They do NOT use mock data. Results populate DISCOVERY.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_LAB = _ROOT / "rubicon-lab"
_RESULTS = _ROOT / "proof" / "raw"
_RESULTS.mkdir(parents=True, exist_ok=True)


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"


def _git(args: list[str], cwd: Path) -> tuple[str, str, int]:
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return r.stdout, r.stderr, r.returncode


def _record(experiment_id: str, data: dict) -> None:
    out = _RESULTS / f"{experiment_id}.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"[{experiment_id}] Recorded → {out}")


def setup_lab() -> None:
    """Initialize lab workspace for experiments."""
    _LAB.mkdir(parents=True, exist_ok=True)
    (_LAB / "tracked.txt").write_text("initial content\n")
    (_LAB / "ignored.txt").write_text("ignored content\n")
    (_LAB / "db").mkdir(exist_ok=True)
    (_LAB / "fixtures" / "http").mkdir(parents=True, exist_ok=True)
    (_LAB / "outside").mkdir(exist_ok=True)

    # Init git
    if not (_LAB / ".git").exists():
        subprocess.run(["git", "init"], cwd=_LAB, capture_output=True)
        subprocess.run(["git", "config", "user.email", "rubicon-lab@experiment.local"],
                       cwd=_LAB, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Rubicon Lab"],
                       cwd=_LAB, capture_output=True)

    # .gitignore
    (_LAB / ".gitignore").write_text("ignored.txt\ndb/\nlogs/\n")

    # Initial commit
    _git(["add", "."], _LAB)
    _git(["commit", "-m", "Initial lab setup", "--allow-empty"], _LAB)

    # Bare remote
    remote_path = _ROOT / "rubicon-lab-remote.git"
    if not remote_path.exists():
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True)
        _git(["remote", "add", "origin", str(remote_path)], _LAB)
        _git(["push", "-u", "origin", "main"], _LAB)

    print("[setup] Lab workspace initialized.")


def experiment_r01() -> dict:
    """R01 — tracked file edit: does rollback restore it exactly?"""
    path = _LAB / "tracked.txt"
    pre_hash = _hash_file(path)

    path.write_text("MODIFIED BY EXPERIMENT R01\n")
    post_action_hash = _hash_file(path)

    # NOTE: Actual rollback is performed by Bob IDE.
    # Record pre/post hashes; human fills in post_rollback_hash after Bob rollback.
    result = {
        "experiment": "R01",
        "description": "tracked file edit",
        "pre_hash": pre_hash,
        "post_action_hash": post_action_hash,
        "post_rollback_hash": "PENDING_HUMAN_BOB_ROLLBACK",
        "restored": "PENDING",
        "notes": "Run Bob rollback after this script, then update post_rollback_hash",
        "hypothesis": "RESTORED",
        "ts": time.time(),
    }
    _record("R01", result)
    return result


def experiment_r03() -> dict:
    """R03 — .gitignore file mutation: does Bob snapshot ignored files?"""
    path = _LAB / "ignored.txt"
    pre_hash = _hash_file(path)

    path.write_text("MODIFIED IGNORED FILE R03\n")
    post_action_hash = _hash_file(path)

    result = {
        "experiment": "R03",
        "description": ".gitignore file mutation",
        "pre_hash": pre_hash,
        "post_action_hash": post_action_hash,
        "post_rollback_hash": "PENDING_HUMAN_BOB_ROLLBACK",
        "restored": "PENDING",
        "notes": "Hypothesis: NOT restored — gitignore files excluded from Bob snapshot",
        "hypothesis": "NOT_RESTORED",
        "ts": time.time(),
    }
    _record("R03", result)
    return result


def experiment_r07() -> dict:
    """R07 — remote Git push: does rollback affect the remote ref?"""
    # Record pre-push remote state
    pre_remote_out, _, _ = _git(["ls-remote", "origin"], _LAB)
    pre_remote_hash = hashlib.sha256(pre_remote_out.encode()).hexdigest()
    head_out, _, _ = _git(["rev-parse", "HEAD"], _LAB)
    pre_head = head_out.strip()

    # Edit + commit + push
    path = _LAB / "tracked.txt"
    path.write_text(f"R07 push experiment {time.time()}\n")
    _git(["add", "tracked.txt"], _LAB)
    _git(["commit", "-m", "R07: pre-push commit"], _LAB)
    _git(["push", "origin", "HEAD:main"], _LAB)

    post_remote_out, _, _ = _git(["ls-remote", "origin"], _LAB)
    post_remote_hash = hashlib.sha256(post_remote_out.encode()).hexdigest()
    post_head_out, _, _ = _git(["rev-parse", "HEAD"], _LAB)
    post_head = post_head_out.strip()

    result = {
        "experiment": "R07",
        "description": "remote Git push",
        "pre_head": pre_head,
        "post_head": post_head,
        "pre_remote_hash": pre_remote_hash,
        "post_action_remote_hash": post_remote_hash,
        "post_rollback_remote_hash": "PENDING_HUMAN_BOB_ROLLBACK",
        "remote_changed": pre_remote_hash != post_remote_hash,
        "hypothesis": "WORKSPACE_RESTORED_REMOTE_UNCHANGED",
        "notes": "Critical demonstration: remote ref should remain CHANGED after Bob rollback",
        "ts": time.time(),
    }
    _record("R07", result)
    return result


def experiment_r08() -> dict:
    """R08 — outside-workspace write."""
    import platform
    if platform.system() == "Windows":
        outside_path = Path(os.environ.get("TEMP", "C:/Windows/Temp")) / f"rubicon-outside-{int(time.time())}.txt"
    else:
        outside_path = Path(f"/tmp/rubicon-outside/{int(time.time())}.txt")

    outside_path.parent.mkdir(parents=True, exist_ok=True)
    outside_path.write_text(f"Outside workspace write R08 {time.time()}\n")
    post_hash = _hash_file(outside_path)

    result = {
        "experiment": "R08",
        "description": "outside-workspace write",
        "outside_path": str(outside_path),
        "post_write_hash": post_hash,
        "post_rollback_hash": "PENDING_HUMAN_BOB_ROLLBACK",
        "hypothesis": "NOT_RESTORED",
        "notes": "Outside-workspace writes should persist after Bob rollback",
        "ts": time.time(),
    }
    _record("R08", result)
    return result


def experiment_r09() -> dict:
    """R09 — local database mutation."""
    import sqlite3
    db_path = _LAB / "db" / "state.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, data TEXT, ts REAL)")
    conn.execute("INSERT INTO events (data, ts) VALUES (?, ?)", (f"R09 event", time.time()))
    conn.commit()
    conn.close()

    post_hash = _hash_file(db_path)

    result = {
        "experiment": "R09",
        "description": "local database mutation",
        "db_path": str(db_path),
        "post_insert_hash": post_hash,
        "post_rollback_hash": "PENDING_HUMAN_BOB_ROLLBACK",
        "hypothesis": "NOT_RESTORED",
        "notes": "DB files are in .gitignore; should not be restored by Bob rollback",
        "ts": time.time(),
    }
    _record("R09", result)
    return result


def experiment_r11() -> dict:
    """R11 — HTTP mutation to disposable fixture."""
    import urllib.request
    import urllib.error

    fixture_url = "http://127.0.0.1:9876"
    event_payload = json.dumps({"type": "R11_test", "ts": time.time()}).encode()

    try:
        req = urllib.request.Request(
            f"{fixture_url}/events",
            data=event_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            status = resp.status
            response_body = resp.read().decode()
    except Exception as exc:
        status = -1
        response_body = str(exc)

    result = {
        "experiment": "R11",
        "description": "HTTP POST to local fixture",
        "fixture_url": fixture_url,
        "post_status": status,
        "response": response_body,
        "post_rollback_event_count": "PENDING_HUMAN_BOB_ROLLBACK",
        "hypothesis": "HTTP_EVENT_PERSISTS_AFTER_ROLLBACK",
        "notes": "Start fixture server first: python3 core/adapters/http_fixture_adapter.py",
        "ts": time.time(),
    }
    _record("R11", result)
    return result


if __name__ == "__main__":
    print("=== RUBICON Phase 0 Discovery Experiments ===\n")
    setup_lab()
    results = {}
    for fn in [experiment_r01, experiment_r03, experiment_r07, experiment_r08, experiment_r09, experiment_r11]:
        try:
            r = fn()
            results[r["experiment"]] = r["hypothesis"]
            print(f"  {r['experiment']}: hypothesis={r['hypothesis']}")
        except Exception as exc:
            print(f"  ERROR in {fn.__name__}: {exc}")

    print(f"\n=== Run Bob rollback after each experiment to complete results ===")
    print(f"Results saved to: {_RESULTS}")
