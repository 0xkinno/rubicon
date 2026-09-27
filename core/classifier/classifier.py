"""
core/classifier/classifier.py

Deterministic effect classifier.

For every proposed Bob tool action, the classifier returns a typed ClassificationResult
and a populated EffectVector. It inspects:
  - tool name
  - structured tool input
  - command text (where applicable)
  - path targets and workspace boundary
  - shell redirection, pipes, and command substitution
  - Git remote destinations
  - process detachment semantics
  - known network mutation patterns

The classifier NEVER uses an AI model to decide reversibility.
UNKNOWN = unsafe (fail closed).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import yaml

from core.models import (
    ClassificationResult,
    EffectVector,
    StateDomain,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RULES_REGISTRY_PATH = _REPO_ROOT / "config" / "rules_registry.yaml"
_ROLLBACK_CONTRACT_PATH = _REPO_ROOT / "config" / "rollback_contract.yaml"

# Shell patterns that produce UNKNOWN_EFFECT (fail closed)
_OPAQUE_SHELL_PATTERNS = re.compile(
    r"^(sh\s+-c|bash\s+-c|zsh\s+-c|/bin/sh\s+-c|/bin/bash\s+-c"
    r"|powershell\s+-Command|pwsh\s+-Command|powershell\.exe\s+-Command"
    r"|node\s+-e|python\s+-c|ruby\s+-e|perl\s+-e)",
    re.IGNORECASE,
)

# Path traversal patterns
_PATH_TRAVERSAL_PATTERNS = re.compile(r"\.\.[/\\]|\.\.$|%2e%2e", re.IGNORECASE)

# Git push patterns
_GIT_PUSH_PATTERN = re.compile(r"^git\s+push\b", re.IGNORECASE)
_GIT_COMMIT_PATTERN = re.compile(r"^git\s+commit\b", re.IGNORECASE)
_GIT_ADD_PATTERN = re.compile(r"^git\s+(add|stage)\b", re.IGNORECASE)
_GIT_READ_PATTERN = re.compile(
    r"^git\s+(log|status|diff|show|branch|remote\s+-v|ls-remote|fetch\s+--dry)", re.IGNORECASE
)

# npm publish
_NPM_PUBLISH_PATTERN = re.compile(r"^npm\s+publish\b", re.IGNORECASE)

# npm safe operations (test, run test, run build, install, ci)
_NPM_TEST_PATTERN = re.compile(r"^npm\s+(test|run\s+test|run\s+lint|run\s+typecheck)\b", re.IGNORECASE)
_NPM_INSTALL_PATTERN = re.compile(r"^npm\s+(install|ci|i)\b", re.IGNORECASE)

# pytest / python test
_PYTHON_TEST_PATTERN = re.compile(r"^(python\s+-m\s+pytest|pytest)\b", re.IGNORECASE)

# pip install
_PIP_INSTALL_PATTERN = re.compile(r"^pip\s+install\b", re.IGNORECASE)

# curl — GET only (no mutation flags)
_CURL_GET_PATTERN = re.compile(r"^curl\s", re.IGNORECASE)

# Network mutation patterns
_CURL_MUTATION_PATTERN = re.compile(
    r"curl\s.*(-X\s*(POST|PUT|PATCH|DELETE)|--data\b|-d\s)", re.IGNORECASE
)

# Background/detached process patterns
_DETACH_PATTERN = re.compile(
    r"(&\s*$|--detach\b|nohup\s|Start-Process\b|setsid\s)", re.IGNORECASE
)

# SQLite database mutation pattern
_SQLITE_PATTERN = re.compile(r"^sqlite3\b", re.IGNORECASE)

# Read-only tools
_READ_ONLY_TOOLS = {
    "read_file",
    "list_files",
    "get_file_info",
    "search_files",
    "grep",
    "glob",
    "GetSymbolsOverview",
    "FindSymbol",
    "FindReferencingSymbols",
}

# PowerShell / system read-only commands
_POWERSHELL_READ_PATTERN = re.compile(
    r"^(Test-Path|Get-ChildItem|Get-Item|Get-Content|Write-Host|Write-Output"
    r"|Select-Object|Select-String|Out-Host|Where-Object|ForEach-Object"
    r"|python\s+--version|node\s+--version|npm\s+--version|git\s+--version"
    r"|pip\s+--version|pip\s+list|pip\s+show"
    r"|ls\s|dir\s|ls$|dir$|echo\s|cat\s|type\s)\b",
    re.IGNORECASE,
)

# python / python3 running a specific named script (not -c inline)
_PYTHON_SCRIPT_PATTERN = re.compile(
    r"^python3?\s+(?!-c\b)(?!-m\s+\S+\s+-c\b)[^\s\"\']+\.py(\s|$)",
    re.IGNORECASE,
)

# python -m pytest / python -m uvicorn etc
_PYTHON_MODULE_PATTERN = re.compile(
    r"^python3?\s+-m\s+(pytest|uvicorn|pip|mypy|ruff|black|isort|coverage)(\s|$)",
    re.IGNORECASE,
)

# make targets
_MAKE_PATTERN = re.compile(
    r"^make\s+(test|clean|install|proof|sessions|demo-r07|clean-room|lint|dev-api|dev-web|keygen|discovery|screenshot)$",
    re.IGNORECASE,
)

# Tracked write tools
_WRITE_TOOLS = {
    "write_file",
    "apply_diff",
    "insert_content",
    "search_and_replace",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _action_id(tool: str, raw_input: dict, session_id: str) -> str:
    cleaned = {k: v for k, v in raw_input.items() if not str(k).startswith("_rubicon_")} if isinstance(raw_input, dict) else raw_input
    payload = json.dumps(
        {"tool": tool, "input": cleaned, "session_id": session_id},
        sort_keys=True, separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _normalize_command(cmd: Any) -> str:
    if not isinstance(cmd, str):
        return ""
    # Collapse whitespace, strip leading/trailing
    return re.sub(r"\s+", " ", cmd.strip())


def _is_inside_workspace(path_str: str, workspace_root: Path) -> bool:
    try:
        target = Path(path_str).resolve()
        target.relative_to(workspace_root.resolve())
        return True
    except (ValueError, TypeError, OSError):
        return False


def _path_matches_gitignore(path_str: str, workspace_root: Path) -> bool:
    """
    Lightweight heuristic gitignore check.
    A full implementation would call gitignore parsing.
    For now: flag common excluded patterns.
    """
    p = path_str.lower()
    excluded_fragments = [
        "node_modules", ".next", "dist/", "build/", "__pycache__",
        ".pytest_cache", ".mypy_cache", "*.log", "*.db", "*.sqlite",
        ".env",
    ]
    return any(frag in p for frag in excluded_fragments)


def _path_matches_env(path_str: str) -> bool:
    name = Path(path_str).name.lower()
    return name == ".env" or name.startswith(".env.")


# ─────────────────────────────────────────────────────────────────────────────
# Main classifier
# ─────────────────────────────────────────────────────────────────────────────

class Classifier:
    """
    Deterministic effect classifier.

    Usage:
        classifier = Classifier(workspace_root=Path("/workspace/myproject"))
        result, vector = classifier.classify(
            tool="execute_command",
            raw_input={"command": "git push origin main"},
            session_id="sess_abc123",
        )
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self._workspace_root = workspace_root or _REPO_ROOT
        self._rules = self._load_rules()
        self._contract = self._load_contract()

    def _load_rules(self) -> list[dict]:
        if _RULES_REGISTRY_PATH.exists():
            with open(_RULES_REGISTRY_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("rules", [])
        return []

    def _load_contract(self) -> dict:
        if _ROLLBACK_CONTRACT_PATH.exists():
            with open(_ROLLBACK_CONTRACT_PATH, encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(
        self,
        tool: str,
        raw_input: dict,
        session_id: str,
    ) -> tuple[ClassificationResult, EffectVector]:
        """
        Classify a proposed tool action.

        Returns:
            (ClassificationResult, EffectVector)
        """
        action_id = _action_id(tool, raw_input, session_id)
        result, vector = self._route(tool, raw_input, action_id, session_id)
        return result, vector

    # ── Internal routing ──────────────────────────────────────────────────────

    def _route(
        self,
        tool: str,
        raw_input: dict,
        action_id: str,
        session_id: str,
    ) -> tuple[ClassificationResult, EffectVector]:
        # 1. Read-only tools — always COVERED_REVERSIBLE
        if tool in _READ_ONLY_TOOLS:
            return self._make_covered(tool, raw_input, action_id, session_id,
                                      "Read-only tool — no state mutation")

        # 2. Write tools — inspect path
        if tool in _WRITE_TOOLS:
            return self._classify_write_tool(tool, raw_input, action_id, session_id)

        # 3. execute_command — detailed inspection
        if tool == "execute_command":
            cmd_raw = raw_input.get("command", raw_input.get("cmd", ""))
            return self._classify_command(cmd_raw, raw_input, action_id, session_id)

        # 4. Any other tool — unknown
        return self._make_unknown(
            tool, raw_input, action_id, session_id,
            f"Unknown tool type '{tool}' — fail closed",
            domains=[StateDomain.UNKNOWN],
        )

    # ── Write tool classification ─────────────────────────────────────────────

    def _classify_write_tool(
        self, tool: str, raw_input: dict, action_id: str, session_id: str
    ) -> tuple[ClassificationResult, EffectVector]:
        path_str = raw_input.get("path", "")

        # .env file
        if _path_matches_env(path_str):
            return self._make_outside(
                tool, raw_input, action_id, session_id,
                f"Writing .env file — CREDENTIAL_STATE outside rollback contract",
                domains=[StateDomain.CREDENTIAL_STATE, StateDomain.WORKSPACE_EXCLUDED],
                paths=[path_str],
            )

        # Outside workspace
        if path_str and not _is_inside_workspace(path_str, self._workspace_root):
            return self._make_outside(
                tool, raw_input, action_id, session_id,
                f"Write path '{path_str}' is outside workspace root",
                domains=[StateDomain.OUTSIDE_WORKSPACE],
                paths=[path_str],
            )

        # .gitignore / excluded
        if path_str and _path_matches_gitignore(path_str, self._workspace_root):
            return ClassificationResult.BOUNDARY_REQUIRES_PERMIT, EffectVector(
                action_id=action_id,
                session_id=session_id,
                tool=tool,
                normalized_action=f"{tool} {path_str}",
                domains=[StateDomain.WORKSPACE_IGNORED],
                paths=[path_str],
                network_targets=[],
                process_lifetime="none",
                rollback_contract="UNKNOWN",
                observability="PARTIAL",
                decision=ClassificationResult.BOUNDARY_REQUIRES_PERMIT,
                reason="Path matches gitignore or excluded category — rollback coverage uncertain",
                raw_input=raw_input,
            )

        # Tracked workspace write
        return self._make_covered(
            tool, raw_input, action_id, session_id,
            "Tracked workspace write — inside rollback contract (hypothesis: pending R01 confirmation)",
            paths=[path_str],
        )

    # ── Command classification ────────────────────────────────────────────────

    def _classify_command(
        self, cmd_raw: Any, raw_input: dict, action_id: str, session_id: str
    ) -> tuple[ClassificationResult, EffectVector]:
        cmd = _normalize_command(cmd_raw)

        # Compound shell operators, pipes, redirections — fail closed (cannot statically resolve transitive effects)
        # Note: 2>&1 stderr redirect is allowed when standalone at end of command
        # Note: operators inside quotes (such as SQL in sqlite3 'INSERT INTO ...;') are not shell operators
        clean_cmd = re.sub(r'\s*2>&1\s*$', '', cmd)
        unquoted = re.sub(r'(\"[^\"]*\"|\'[^\']*\')', '""', clean_cmd)
        if re.search(r'(&&|\|\||;|\$\(|(?<![A-Za-z0-9_])`[^`\n]+`|(?<!2)>|(?<!\|)\|(?!\|))', unquoted):
            return self._make_unknown(
                "execute_command", raw_input, action_id, session_id,
                "Compound shell operators (&&, ||, ;, |, >, $(), backtick) — transitive effects unresolvable — fail closed",
                domains=[StateDomain.UNKNOWN],
            )

        # Path traversal — fail closed
        if _PATH_TRAVERSAL_PATTERNS.search(cmd):
            return self._make_unknown(
                "execute_command", raw_input, action_id, session_id,
                "Command contains path traversal pattern — fail closed",
                domains=[StateDomain.OUTSIDE_WORKSPACE, StateDomain.UNKNOWN],
            )

        # Opaque shell — fail closed
        if _OPAQUE_SHELL_PATTERNS.match(cmd):
            return self._make_unknown(
                "execute_command", raw_input, action_id, session_id,
                "Opaque inline shell execution — transitive effects unresolvable — fail closed",
                domains=[StateDomain.UNKNOWN],
            )

        # Background process
        if _DETACH_PATTERN.search(cmd):
            return self._make_outside(
                "execute_command", raw_input, action_id, session_id,
                "Detached/background process — persists after rollback",
                domains=[StateDomain.PROCESS_RUNTIME],
            )

        # git push
        if _GIT_PUSH_PATTERN.match(cmd):
            return self._make_outside(
                "execute_command", raw_input, action_id, session_id,
                "git push — mutates VCS_REMOTE which is outside Bob rollback contract",
                domains=[StateDomain.VCS_REMOTE],
                network_targets=self._extract_git_remote(cmd),
            )

        # npm publish
        if _NPM_PUBLISH_PATTERN.match(cmd):
            return self._make_outside(
                "execute_command", raw_input, action_id, session_id,
                "npm publish — mutates PACKAGE_REGISTRY which is outside Bob rollback contract",
                domains=[StateDomain.PACKAGE_REGISTRY, StateDomain.EXTERNAL_NETWORK],
            )

        # curl mutation
        if _CURL_MUTATION_PATTERN.search(cmd):
            return self._make_outside(
                "execute_command", raw_input, action_id, session_id,
                "curl with mutation method (POST/PUT/PATCH/DELETE) — EXTERNAL_NETWORK outside rollback",
                domains=[StateDomain.EXTERNAL_NETWORK],
            )

        # sqlite3 mutation
        if _SQLITE_PATTERN.match(cmd):
            return self._make_outside(
                "execute_command", raw_input, action_id, session_id,
                "sqlite3 — mutates DATABASE_STATE which is outside Bob rollback contract",
                domains=[StateDomain.DATABASE_STATE],
            )

        # git commit
        if _GIT_COMMIT_PATTERN.match(cmd):
            return ClassificationResult.BOUNDARY_REQUIRES_PERMIT, EffectVector(
                action_id=action_id,
                session_id=session_id,
                tool="execute_command",
                normalized_action=cmd,
                domains=[StateDomain.VCS_LOCAL],
                paths=[],
                network_targets=[],
                process_lifetime="none",
                rollback_contract="UNKNOWN",
                observability="VERIFIABLE",
                decision=ClassificationResult.BOUNDARY_REQUIRES_PERMIT,
                reason="git commit mutates VCS_LOCAL — rollback behavior requires R06 confirmation",
                raw_input=raw_input,
            )

        # git add/stage
        if _GIT_ADD_PATTERN.match(cmd):
            return ClassificationResult.BOUNDARY_REQUIRES_PERMIT, EffectVector(
                action_id=action_id,
                session_id=session_id,
                tool="execute_command",
                normalized_action=cmd,
                domains=[StateDomain.WORKSPACE_TRACKED, StateDomain.VCS_LOCAL],
                paths=[],
                network_targets=[],
                process_lifetime="none",
                rollback_contract="UNKNOWN",
                observability="VERIFIABLE",
                decision=ClassificationResult.BOUNDARY_REQUIRES_PERMIT,
                reason="git add modifies Git staging area — R06 experiment needed",
                raw_input=raw_input,
            )

        # git read — safe
        if _GIT_READ_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "Git read-only command — no state mutation",
            )

        # npm test / run test — safe
        if _NPM_TEST_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "npm test/lint/typecheck — read-only execution, no persistent side effects",
            )

        # npm install — boundary (network + node_modules excluded from rollback)
        if _NPM_INSTALL_PATTERN.match(cmd):
            return ClassificationResult.BOUNDARY_REQUIRES_PERMIT, EffectVector(
                action_id=action_id,
                session_id=session_id,
                tool="execute_command",
                normalized_action=cmd,
                domains=[StateDomain.WORKSPACE_EXCLUDED, StateDomain.EXTERNAL_NETWORK],
                paths=[],
                network_targets=[],
                process_lifetime="none",
                rollback_contract="UNKNOWN",
                observability="PARTIAL",
                decision=ClassificationResult.BOUNDARY_REQUIRES_PERMIT,
                reason="npm install modifies node_modules (excluded from rollback) and downloads from network",
                raw_input=raw_input,
            )

        # pytest / python -m pytest — safe
        if _PYTHON_TEST_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "pytest — read-only test execution, no persistent side effects",
            )

        # pip install — boundary
        if _PIP_INSTALL_PATTERN.match(cmd):
            return ClassificationResult.BOUNDARY_REQUIRES_PERMIT, EffectVector(
                action_id=action_id,
                session_id=session_id,
                tool="execute_command",
                normalized_action=cmd,
                domains=[StateDomain.WORKSPACE_EXCLUDED, StateDomain.EXTERNAL_NETWORK],
                paths=[],
                network_targets=[],
                process_lifetime="none",
                rollback_contract="UNKNOWN",
                observability="PARTIAL",
                decision=ClassificationResult.BOUNDARY_REQUIRES_PERMIT,
                reason="pip install modifies venv/packages (excluded from rollback) and downloads from network",
                raw_input=raw_input,
            )

        # curl GET only — safe (must check AFTER mutation pattern)
        if _CURL_GET_PATTERN.match(cmd) and not _CURL_MUTATION_PATTERN.search(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "curl GET — read-only HTTP request, no persistent mutation",
            )

        # PowerShell / system read-only commands
        if _POWERSHELL_READ_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "PowerShell/system read-only command — no state mutation",
            )

        # python script.py (not -c inline)
        if _PYTHON_SCRIPT_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "python named script — allowed (effects classified by script content separately)",
            )

        # python -m pytest / uvicorn / pip etc
        if _PYTHON_MODULE_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "python -m module — allowed (pytest/uvicorn/pip module invocation)",
            )

        # make <known-safe-target>
        if _MAKE_PATTERN.match(cmd):
            return self._make_covered(
                "execute_command", raw_input, action_id, session_id,
                "make target — allowed (known-safe build target)",
            )

        # Default for unmatched commands — fail closed
        return self._make_unknown(
            "execute_command", raw_input, action_id, session_id,
            f"Command not matched by any rule — fail closed: '{cmd[:80]}'",
            domains=[StateDomain.UNKNOWN],
        )

    # ── Factory helpers ───────────────────────────────────────────────────────

    def _make_covered(
        self, tool: str, raw_input: dict, action_id: str, session_id: str,
        reason: str, paths: list[str] = None, domains: list[StateDomain] = None
    ) -> tuple[ClassificationResult, EffectVector]:
        return ClassificationResult.COVERED_REVERSIBLE, EffectVector(
            action_id=action_id,
            session_id=session_id,
            tool=tool,
            normalized_action=_normalize_command(raw_input.get("command", tool)),
            domains=[d.value if isinstance(d, StateDomain) else d
                     for d in (domains or [StateDomain.WORKSPACE_TRACKED])],
            paths=paths or [],
            network_targets=[],
            process_lifetime="none",
            rollback_contract="INSIDE",
            observability="VERIFIABLE",
            decision=ClassificationResult.COVERED_REVERSIBLE,
            reason=reason,
            raw_input=raw_input,
        )

    def _make_outside(
        self, tool: str, raw_input: dict, action_id: str, session_id: str,
        reason: str, domains: list[StateDomain] = None,
        paths: list[str] = None, network_targets: list[str] = None
    ) -> tuple[ClassificationResult, EffectVector]:
        return ClassificationResult.OUTSIDE_ROLLBACK, EffectVector(
            action_id=action_id,
            session_id=session_id,
            tool=tool,
            normalized_action=_normalize_command(raw_input.get("command", tool)),
            domains=[d.value if isinstance(d, StateDomain) else d
                     for d in (domains or [StateDomain.UNKNOWN])],
            paths=paths or [],
            network_targets=network_targets or [],
            process_lifetime="none",
            rollback_contract="OUTSIDE",
            observability="VERIFIABLE",
            decision=ClassificationResult.OUTSIDE_ROLLBACK,
            reason=reason,
            raw_input=raw_input,
        )

    def _make_unknown(
        self, tool: str, raw_input: dict, action_id: str, session_id: str,
        reason: str, domains: list[StateDomain] = None
    ) -> tuple[ClassificationResult, EffectVector]:
        return ClassificationResult.UNKNOWN_EFFECT, EffectVector(
            action_id=action_id,
            session_id=session_id,
            tool=tool,
            normalized_action=_normalize_command(raw_input.get("command", tool)),
            domains=[d.value if isinstance(d, StateDomain) else d
                     for d in (domains or [StateDomain.UNKNOWN])],
            paths=[],
            network_targets=[],
            process_lifetime="unknown",
            rollback_contract="UNKNOWN",
            observability="NOT_OBSERVABLE",
            decision=ClassificationResult.UNKNOWN_EFFECT,
            reason=reason,
            raw_input=raw_input,
        )

    @staticmethod
    def _extract_git_remote(cmd: str) -> list[str]:
        """Extract remote names from git push command."""
        parts = cmd.split()
        # git push [<remote>] [<refspec>]
        if len(parts) >= 3:
            return [parts[2]]
        elif len(parts) >= 2:
            return ["origin"]
        return []
