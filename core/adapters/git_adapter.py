"""
core/adapters/git_adapter.py

Git state verifier adapter.
Captures HEAD, refs, local commit history, remote refs.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


class GitAdapter:
    """
    Adapter for VCS_LOCAL and VCS_REMOTE state domains.
    """

    def __init__(self, workspace_root: Path, remote_name: str = "origin") -> None:
        self._root = workspace_root.resolve()
        self._remote = remote_name

    def hash_state(self, manifest) -> str:
        """Hash git state from a captured manifest."""
        if hasattr(manifest, "git_state"):
            git = manifest.git_state
        elif isinstance(manifest, dict):
            git = manifest.get("git_state", {})
        else:
            git = {}

        if not git:
            return ""

        # Deterministic hash of the git state snapshot
        payload = json.dumps(git, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def hash_remote_state(self) -> str:
        """
        Independently query remote refs and return their hash.
        This is the ground-truth check for VCS_REMOTE.
        """
        try:
            result = subprocess.run(
                ["git", "ls-remote", self._remote],
                capture_output=True, text=True, cwd=self._root,
            )
            if result.returncode == 0:
                return hashlib.sha256(result.stdout.encode()).hexdigest()
            return ""
        except Exception:
            return ""

    def get_head(self) -> str:
        """Return current HEAD SHA."""
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self._root,
            )
            return r.stdout.strip() if r.returncode == 0 else "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def get_remote_refs(self) -> dict[str, str]:
        """Return remote refs as {refname: sha}."""
        refs: dict[str, str] = {}
        try:
            r = subprocess.run(
                ["git", "ls-remote", self._remote],
                capture_output=True, text=True, cwd=self._root,
            )
            for line in r.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    refs[parts[1].strip()] = parts[0].strip()
        except Exception:
            pass
        return refs
