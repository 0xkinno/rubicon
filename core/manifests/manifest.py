"""
core/manifests/manifest.py

Baseline, post-action, and post-rollback manifest capture.
Model-free: no AI inference. Pure deterministic hashing.

Never stores secret values — only hashes and redacted metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Manifest data structure
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FileEntry:
    path: str         # relative to workspace root
    sha256: str
    size: int
    exists: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GitState:
    head: str              # current HEAD SHA or "UNKNOWN"
    branch: str
    working_tree_clean: bool
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]
    remote_refs: dict[str, str]   # remote name → ref SHA

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Manifest:
    manifest_id: str
    captured_at: float
    workspace_root: str
    manifest_type: str    # "baseline" | "post_action" | "post_rollback"
    session_id: str
    policy_version: str
    verifier_version: str
    tracked_files: list[dict]
    git_state: Optional[dict]
    env_state_redacted: dict   # hashes only — never values
    process_snapshot: list[dict]
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def sha256(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Manifest capturer
# ─────────────────────────────────────────────────────────────────────────────

class ManifestCapturer:
    """
    Captures workspace state manifests at defined checkpoints.
    """

    POLICY_VERSION = os.environ.get("RUBICON_POLICY_VERSION", "1.0.0")
    VERIFIER_VERSION = os.environ.get("RUBICON_VERIFIER_VERSION", "1.0.0")

    def __init__(self, workspace_root: Path, session_id: str) -> None:
        self._root = workspace_root.resolve()
        self._session_id = session_id

    def capture(self, manifest_type: str, notes: str = "") -> Manifest:
        """Capture a manifest of the current state."""
        import uuid
        return Manifest(
            manifest_id=str(uuid.uuid4()),
            captured_at=time.time(),
            workspace_root=str(self._root),
            manifest_type=manifest_type,
            session_id=self._session_id,
            policy_version=self.POLICY_VERSION,
            verifier_version=self.VERIFIER_VERSION,
            tracked_files=self._capture_tracked_files(),
            git_state=self._capture_git_state(),
            env_state_redacted=self._capture_env_state(),
            process_snapshot=self._capture_processes(),
            notes=notes,
        )

    # ── File capture ──────────────────────────────────────────────────────────

    def _capture_tracked_files(self) -> list[dict]:
        """Hash all tracked Git files in workspace."""
        entries = []
        try:
            result = subprocess.run(
                ["git", "ls-files", "-z"],
                capture_output=True, text=True, cwd=self._root,
            )
            if result.returncode == 0:
                paths = [p for p in result.stdout.split("\0") if p]
                for rel_path in paths:
                    full_path = self._root / rel_path
                    entry = self._hash_file(rel_path, full_path)
                    entries.append(entry.to_dict())
        except Exception as exc:
            entries.append({"error": str(exc)})
        return entries

    def _hash_file(self, rel_path: str, full_path: Path) -> FileEntry:
        if full_path.is_file():
            data = full_path.read_bytes()
            return FileEntry(
                path=rel_path,
                sha256=hashlib.sha256(data).hexdigest(),
                size=len(data),
                exists=True,
            )
        return FileEntry(path=rel_path, sha256="", size=0, exists=False)

    def hash_single_file(self, path: Path) -> str:
        """Hash a single file, returning its SHA256 or empty string if not found."""
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except (FileNotFoundError, OSError):
            return ""

    # ── Git state ─────────────────────────────────────────────────────────────

    def _capture_git_state(self) -> Optional[dict]:
        try:
            head = self._git_output(["rev-parse", "HEAD"]).strip() or "UNKNOWN"
            branch = self._git_output(["rev-parse", "--abbrev-ref", "HEAD"]).strip()

            status_out = self._git_output(["status", "--porcelain"])
            staged = [l[3:].strip() for l in status_out.splitlines() if l[:2] in {"A ", "M ", "D "}]
            modified = [l[3:].strip() for l in status_out.splitlines() if l[1] == "M"]
            untracked = [l[3:].strip() for l in status_out.splitlines() if l[:2] == "??"]

            # Remote refs — for demo adapter: just origin
            remote_refs: dict[str, str] = {}
            ls_remote = self._git_output(["ls-remote", "--heads", "origin"])
            for line in ls_remote.splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    remote_refs[parts[1].strip()] = parts[0].strip()

            return GitState(
                head=head,
                branch=branch,
                working_tree_clean=not bool(status_out.strip()),
                staged_files=staged,
                modified_files=modified,
                untracked_files=untracked,
                remote_refs=remote_refs,
            ).to_dict()

        except Exception as exc:
            return {"error": str(exc)}

    def _git_output(self, args: list[str]) -> str:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=self._root,
        )
        return r.stdout if r.returncode == 0 else ""

    # ── Env state ─────────────────────────────────────────────────────────────

    def _capture_env_state(self) -> dict:
        """
        Capture hashes of environment-adjacent files WITHOUT storing values.
        """
        state = {}
        env_paths = [
            self._root / ".env",
            self._root / ".env.local",
            self._root / ".env.example",
        ]
        for p in env_paths:
            if p.exists():
                state[p.name] = {
                    "exists": True,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "size": p.stat().st_size,
                }
            else:
                state[p.name] = {"exists": False}
        return state

    # ── Process snapshot ──────────────────────────────────────────────────────

    def _capture_processes(self) -> list[dict]:
        """
        Lightweight process snapshot — only PIDs and normalized commands.
        """
        procs = []
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    cmd_str = " ".join(cmdline[:4])  # truncate for safety
                    procs.append({
                        "pid": proc.info["pid"],
                        "name": proc.info.get("name", ""),
                        "cmd_prefix": cmd_str[:80],
                        "cmd_hash": hashlib.sha256(
                            " ".join(cmdline).encode()
                        ).hexdigest(),
                        "create_time": proc.info.get("create_time"),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            procs = [{"error": "psutil not installed — process snapshot unavailable"}]
        return procs
