"""
core/adapters/filesystem_adapter.py

Filesystem verifier adapter.
Hashes tracked file content, ignored files where accessible,
outside-workspace test files, directory inventories.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional


class FilesystemAdapter:
    """
    Adapter for WORKSPACE_TRACKED, WORKSPACE_IGNORED, WORKSPACE_EXCLUDED, OUTSIDE_WORKSPACE.
    """

    def __init__(self, workspace_root: Path, extra_paths: list[Path] = None) -> None:
        self._root = workspace_root.resolve()
        self._extra_paths = extra_paths or []

    def hash_state(self, manifest) -> str:
        """
        Hash the tracked file tree as recorded in the manifest.
        Returns a deterministic aggregate hash.
        """
        files = manifest.tracked_files if hasattr(manifest, "tracked_files") else []
        if isinstance(manifest, dict):
            files = manifest.get("tracked_files", [])
        aggregate = json.dumps(
            sorted(files, key=lambda x: x.get("path", "")),
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(aggregate.encode()).hexdigest()

    def hash_single_path(self, path: Path) -> str:
        """Hash a single file for direct comparison."""
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except (FileNotFoundError, OSError):
            return ""

    def snapshot_paths(self, paths: list[Path]) -> dict[str, str]:
        """Hash multiple specific paths."""
        return {str(p): self.hash_single_path(p) for p in paths}
