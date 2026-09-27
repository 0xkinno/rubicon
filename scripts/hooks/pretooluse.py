#!/usr/bin/env python3
"""
scripts/hooks/pretooluse.py

Rubicon PreToolUse hook.

IBM Bob calls this before every matched tool.
Exit code 2 = block the tool.
Exit code 0 = allow.

stdin: JSON with tool_name and tool_input from Bob.
stderr: human-readable reason (shown in Bob IDE).
stdout: IGNORED by Bob per PreToolUse behavior.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ── Add repo root to path ────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from core.classifier import Classifier
from core.models import ClassificationResult
from core.permits import PermitEngine


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

_WORKSPACE_ROOT = Path(os.environ.get("RUBICON_WORKSPACE_ROOT", str(_ROOT)))
_PERMIT_STORE = Path(os.environ.get("RUBICON_PERMIT_STORE",
                                    str(Path.home() / ".rubicon" / "permits")))
_PUBLIC_KEY_PATH = _ROOT / "keys" / "rubicon-verifier.pub.pem"
_priv_env = os.environ.get("RUBICON_SIGNING_KEY_PATH")
if _priv_env:
    _PRIVATE_KEY_PATH = Path(_priv_env)
else:
    _default_priv = Path.home() / ".rubicon" / "rubicon-signer.key"
    _PRIVATE_KEY_PATH = _default_priv if _default_priv.is_file() else None

# Session ID from Bob env or fallback
_SESSION_ID = os.environ.get("BOB_SESSION_ID", os.environ.get("RUBICON_SESSION_ID", "unknown"))

# ─────────────────────────────────────────────────────────────────────────────
# Decision ledger (append-only JSONL log)
# ─────────────────────────────────────────────────────────────────────────────

_LEDGER_PATH = _ROOT / "data" / "decisions.jsonl"


def _log_decision(entry: dict) -> None:
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _send_telemetry(entry: dict) -> None:
    """Send redacted event metadata to deployed Rubicon dashboard (observer telemetry only)."""
    api_url = os.environ.get("RUBICON_API_URL") or os.environ.get("NEXT_PUBLIC_RUBICON_API_URL")
    if not api_url:
        return

    # Strict metadata-only payload: NO commands, secrets, file contents, env vars
    payload = {
        "timestamp": entry.get("ts"),
        "session_id": entry.get("session_id"),
        "tool": entry.get("tool"),
        "action_id": entry.get("action_id"),
        "classification": entry.get("classification"),
        "domains": entry.get("domains", []),
        "decision": entry.get("decision"),
        "permit_id_present": bool(entry.get("permit_id")),
    }

    token = os.environ.get("RUBICON_TELEMETRY_TOKEN", "")
    url = f"{api_url.rstrip('/')}/api/telemetry/decision"

    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=1.2):
            pass
    except Exception:
        # Telemetry is strictly observer-only and must NEVER disrupt or delay Bob
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Main hook logic
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    # Read Bob's JSON input from stdin
    # If not called by Bob (no JSON input), allow through
    try:
        import select
        # On Windows, just try to read; on Unix we can check stdin
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        if not raw.strip():
            # Not invoked by Bob hook (no structured input) — allow through
            return 0
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[RUBICON] BLOCK: malformed hook input — {exc}", file=sys.stderr)
        return 2  # fail closed
    except Exception:
        # Cannot read stdin (interactive context) — allow through
        return 0

    tool_name = data.get("tool_name", data.get("tool", ""))
    tool_input = data.get("tool_input", data.get("input", {}))

    if not tool_name:
        print("[RUBICON] BLOCK: missing tool_name in hook input — fail closed", file=sys.stderr)
        return 2

    # Internal Bob meta-tools are not file/command operations — always allow
    _INTERNAL_TOOLS = {
        "update_todo_list", "ask_followup_question", "start_subtask",
        "start_workflow", "use_skill", "switch_mode", "create_html_artifact",
        "create_chart", "spawn_subagent", "list_ibm_doc_libraries",
        "search_ibm_docs", "office_read", "office_edit",
        "find_symbol", "FindSymbol", "FindReferencingSymbols",
        "GetSymbolsOverview", "GetSymbols",
    }
    if tool_name in _INTERNAL_TOOLS:
        return 0

    # ── Classify ────────────────────────────────────────────────────────────
    classifier = Classifier(workspace_root=_WORKSPACE_ROOT)
    result, vector = classifier.classify(
        tool=tool_name,
        raw_input=tool_input if isinstance(tool_input, dict) else {"command": str(tool_input)},
        session_id=_SESSION_ID,
    )

    # ── Check for pending permit ─────────────────────────────────────────────
    permit_id = (
        tool_input.get("_rubicon_permit_id")
        if isinstance(tool_input, dict) else None
    )

    # ── Decision routing ─────────────────────────────────────────────────────
    exit_code = 0
    block_reason = ""

    if result == ClassificationResult.COVERED_REVERSIBLE:
        # Allow — no action needed
        exit_code = 0

    elif result == ClassificationResult.BOUNDARY_REQUIRES_PERMIT:
        if permit_id and _PUBLIC_KEY_PATH.exists():
            # Validate the permit
            try:
                import subprocess
                head = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True, text=True, cwd=_WORKSPACE_ROOT,
                ).stdout.strip() or "UNKNOWN"

                engine = PermitEngine(
                    permit_store_dir=_PERMIT_STORE,
                    public_key_path=_PUBLIC_KEY_PATH,
                    private_key_path=_PRIVATE_KEY_PATH if (_PRIVATE_KEY_PATH and _PRIVATE_KEY_PATH.is_file()) else None,
                )
                valid, reason = engine.validate_and_consume(
                    permit_id=permit_id,
                    action_id=vector.action_id,
                    session_id=_SESSION_ID,
                    tool=tool_name,
                    normalized_action=vector.normalized_action,
                    head_commit=head,
                )
                if valid:
                    exit_code = 0
                else:
                    exit_code = 2
                    block_reason = f"Permit validation failed: {reason}"
            except Exception as exc:
                exit_code = 2
                block_reason = f"Permit validation error — fail closed: {exc}"
        else:
            # No permit provided — block and request human decision
            exit_code = 2
            block_reason = (
                f"Action requires human permit (BOUNDARY_REQUIRES_PERMIT).\n"
                f"Action: {vector.normalized_action}\n"
                f"Domains: {', '.join(vector.domains)}\n"
                f"Reason: {vector.reason}\n\n"
                f"To approve:\n"
                f"  python3 cli/rubicon.py approve --action-id {vector.action_id} --session {_SESSION_ID}\n"
                f"Then re-run the Bob task with _rubicon_permit_id in the tool input."
            )

    elif result in (ClassificationResult.OUTSIDE_ROLLBACK, ClassificationResult.UNKNOWN_EFFECT,
                    ClassificationResult.UNOBSERVABLE_EFFECT, ClassificationResult.DENY_POLICY):
        if permit_id and _PUBLIC_KEY_PATH.exists():
            # Even OUTSIDE_ROLLBACK can be permitted with explicit human decision
            try:
                import subprocess
                head = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True, text=True, cwd=_WORKSPACE_ROOT,
                ).stdout.strip() or "UNKNOWN"

                engine = PermitEngine(
                    permit_store_dir=_PERMIT_STORE,
                    public_key_path=_PUBLIC_KEY_PATH,
                    private_key_path=_PRIVATE_KEY_PATH if (_PRIVATE_KEY_PATH and _PRIVATE_KEY_PATH.is_file()) else None,
                )
                valid, reason = engine.validate_and_consume(
                    permit_id=permit_id,
                    action_id=vector.action_id,
                    session_id=_SESSION_ID,
                    tool=tool_name,
                    normalized_action=vector.normalized_action,
                    head_commit=head,
                )
                if valid:
                    exit_code = 0
                else:
                    exit_code = 2
                    block_reason = f"Permit invalid: {reason}"
            except Exception as exc:
                exit_code = 2
                block_reason = f"Permit error — fail closed: {exc}"
        else:
            exit_code = 2
            block_reason = (
                f"BLOCKED — {result.value}\n"
                f"Tool: {tool_name}\n"
                f"Action: {vector.normalized_action}\n"
                f"Domains: {', '.join(vector.domains)}\n"
                f"Rollback contract: {vector.rollback_contract}\n"
                f"Reason: {vector.reason}\n\n"
                f"This action is outside Bob's rollback contract or has unknown effects.\n"
                f"To explicitly approve:\n"
                f"  python3 cli/rubicon.py approve --action-id {vector.action_id} --session {_SESSION_ID}"
            )

    # ── Auto-register pending permit if blocked ──────────────────────────────
    if exit_code != 0 and _PUBLIC_KEY_PATH.exists():
        try:
            import subprocess
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=_WORKSPACE_ROOT,
            ).stdout.strip() or "UNKNOWN"
            engine = PermitEngine(
                permit_store_dir=_PERMIT_STORE,
                public_key_path=_PUBLIC_KEY_PATH,
            )
            existing = [p for p in engine.list_pending() if p.action_id == vector.action_id]
            if not existing:
                engine.create_pending(vector, head)
        except Exception:
            pass

    # ── Log decision & send observer telemetry ────────────────────────────────
    import time
    log_entry = {
        "ts": time.time(),
        "session_id": _SESSION_ID,
        "tool": tool_name,
        "action_id": vector.action_id,
        "normalized_action": vector.normalized_action,
        "classification": result.value,
        "domains": vector.domains,
        "decision": "ALLOW" if exit_code == 0 else "BLOCK",
        "reason": block_reason or vector.reason,
        "permit_id": permit_id,
    }
    _log_decision(log_entry)
    _send_telemetry(log_entry)

    # ── Emit block reason to stderr (visible in Bob IDE) ─────────────────────
    if exit_code != 0:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[RUBICON] BLOCKED — {result.value}", file=sys.stderr)
        print(block_reason, file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
