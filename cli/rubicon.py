#!/usr/bin/env python3
"""
cli/rubicon.py

Rubicon CLI — human-facing command interface.

Commands:
  approve   — Issue a one-use signed permit for a pending blocked action
  status    — Show current session status and pending decisions
  verify    — Run independent post-rollback verification
  receipts  — List and display reversibility receipts
  keygen    — Generate Ed25519 signing keypair (private key goes OUTSIDE workspace)
  sessions  — Show bob_sessions summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from core.permits import PermitEngine, Permit
from core.models import PermitState


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

_PERMIT_STORE = Path(os.environ.get("RUBICON_PERMIT_STORE",
                                    str(Path.home() / ".rubicon" / "permits")))
_PUBLIC_KEY_PATH = _ROOT / "keys" / "rubicon-verifier.pub.pem"
_priv_env = os.environ.get("RUBICON_SIGNING_KEY_PATH")
if _priv_env:
    _PRIVATE_KEY_PATH = Path(_priv_env)
else:
    _default_priv = Path.home() / ".rubicon" / "rubicon-signer.key"
    _PRIVATE_KEY_PATH = _default_priv

_RECEIPTS_DIR = _ROOT / "proof" / "receipts"
_DECISIONS_LOG = _ROOT / "data" / "decisions.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# Subcommands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_approve(args: argparse.Namespace) -> int:
    """Issue a signed permit for a pending or new action."""
    if not _PRIVATE_KEY_PATH or not _PRIVATE_KEY_PATH.is_file():
        print(f"ERROR: Signing key not found at {_PRIVATE_KEY_PATH}")
        print("Set RUBICON_SIGNING_KEY_PATH to the private key location outside the workspace.")
        print("Generate a keypair: python3 cli/rubicon.py keygen")
        return 1

    if not _PUBLIC_KEY_PATH.exists():
        print(f"ERROR: Public key not found at {_PUBLIC_KEY_PATH}")
        print("Run: python3 cli/rubicon.py keygen")
        return 1

    engine = PermitEngine(
        permit_store_dir=_PERMIT_STORE,
        public_key_path=_PUBLIC_KEY_PATH,
        private_key_path=_PRIVATE_KEY_PATH,
    )

    # Find by permit_id if given, otherwise show pending list
    if args.permit_id:
        permit_id = args.permit_id
    elif args.action_id:
        # Find pending permit for this action
        pending = engine.list_pending()
        matching = [p for p in pending if p.action_id == args.action_id]
        if not matching:
            # Reconstruct from decisions ledger if available
            ledger_path = _ROOT / "data" / "decisions.jsonl"
            found_entry = None
            if ledger_path.exists():
                for line in reversed(ledger_path.read_text(encoding="utf-8").splitlines()):
                    try:
                        e = json.loads(line)
                        if e.get("action_id") == args.action_id:
                            found_entry = e
                            break
                    except Exception:
                        pass
            if found_entry:
                head = "UNKNOWN"
                try:
                    import subprocess
                    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_ROOT).stdout.strip() or "UNKNOWN"
                except Exception:
                    pass
                from core.models import EffectVector
                vec = EffectVector(
                    action_id=found_entry["action_id"],
                    session_id=found_entry.get("session_id", "default"),
                    tool=found_entry.get("tool", "execute_command"),
                    normalized_action=found_entry.get("normalized_action", "git push origin main"),
                    domains=found_entry.get("domains", []),
                    paths=[],
                    network_targets=[],
                    process_lifetime="none",
                    rollback_contract="OUTSIDE",
                    observability={},
                    reason="Approved via CLI",
                    decision="BLOCK",
                )
                new_p = engine.create_pending(vec, head)
                permit_id = new_p.permit_id
            else:
                print(f"No pending permit found for action_id={args.action_id}")
                print("Create one first: python3 cli/rubicon.py status")
                return 1
        else:
            permit_id = matching[0].permit_id
    else:
        # List pending
        pending = engine.list_pending()
        if not pending:
            print("No pending permits.")
            return 0
        print(f"\n{'='*60}")
        print("PENDING PERMITS — Choose one to approve")
        print(f"{'='*60}")
        for p in pending:
            print(f"\n  Permit ID: {p.permit_id}")
            print(f"  Action:    {p.action_id}")
            print(f"  Tool:      {p.tool}")
            print(f"  Session:   {p.session_id}")
        print(f"\nTo approve: python3 cli/rubicon.py approve --permit-id <ID>")
        return 0

    try:
        permit = engine.issue_signed(permit_id)
        print(f"\n{'='*60}")
        print("[RUBICON] PERMIT ISSUED")
        print(f"{'='*60}")
        print(f"Permit ID:  {permit.permit_id}")
        print(f"Action ID:  {permit.action_id}")
        print(f"Tool:       {permit.tool}")
        print(f"Expires:    {permit.expires_at:.0f}")
        print(f"Signature:  {permit.signature[:32]}...")
        print(f"\nAdd _rubicon_permit_id={permit.permit_id} to the tool input and retry.")
        print(f"{'='*60}\n")
        return 0
    except Exception as exc:
        print(f"ERROR issuing permit: {exc}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show current session status."""
    print(f"\n{'='*60}")
    print("RUBICON STATUS")
    print(f"{'='*60}")

    # Recent decisions
    if _DECISIONS_LOG.exists():
        lines = _DECISIONS_LOG.read_text(encoding="utf-8").splitlines()
        recent = lines[-20:] if len(lines) > 20 else lines
        print(f"\nRecent decisions ({len(lines)} total):")
        for line in recent[-5:]:
            try:
                d = json.loads(line)
                print(f"  [{d.get('decision','?')}] {d.get('tool','?')} → {d.get('classification','?')}")
            except Exception:
                pass

    # Pending permits
    if _PUBLIC_KEY_PATH.exists():
        try:
            engine = PermitEngine(
                permit_store_dir=_PERMIT_STORE,
                public_key_path=_PUBLIC_KEY_PATH,
            )
            pending = engine.list_pending()
            print(f"\nPending permits: {len(pending)}")
            for p in pending:
                print(f"  {p.permit_id[:12]}... — {p.tool} — {p.action_id[:12]}...")
        except Exception as exc:
            print(f"  (cannot read permits: {exc})")
    print(f"{'='*60}\n")
    return 0


def cmd_receipts(args: argparse.Namespace) -> int:
    """List and display reversibility receipts."""
    if not _RECEIPTS_DIR.exists():
        print("No receipts found.")
        return 0

    receipts = sorted(_RECEIPTS_DIR.glob("*.json"), reverse=True)
    if not receipts:
        print("No receipts found.")
        return 0

    if args.receipt_id:
        target = _RECEIPTS_DIR / f"{args.receipt_id}.json"
        if target.exists():
            data = json.loads(target.read_text())
            print(json.dumps(data, indent=2))
        else:
            print(f"Receipt not found: {args.receipt_id}")
            return 1
    else:
        print(f"\n{'='*60}")
        print(f"REVERSIBILITY RECEIPTS ({len(receipts)} total)")
        print(f"{'='*60}")
        for r in receipts[:10]:
            try:
                data = json.loads(r.read_text())
                print(f"\n  {r.stem[:16]}...")
                print(f"  Session:  {data.get('session_id','?')[:16]}")
                print(f"  Verdict:  {data.get('decision','?')}")
                print(f"  Domains:  {[dr.get('domain') for dr in data.get('domain_results', [])]}")
            except Exception:
                pass
        print(f"\nTo view details: python3 cli/rubicon.py receipts --id <ID>")
        print(f"{'='*60}\n")
    return 0


def cmd_keygen(args: argparse.Namespace) -> int:
    """Generate Ed25519 signing keypair."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    key = Ed25519PrivateKey.generate()
    pub = key.public_key()

    # Private key — goes OUTSIDE workspace
    priv_path = Path(args.private_key_out)
    priv_path.parent.mkdir(parents=True, exist_ok=True)
    priv_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path.write_bytes(priv_bytes)
    priv_path.chmod(0o600)

    # Public key — goes IN repository
    pub_path = _ROOT / "keys" / "rubicon-verifier.pub.pem"
    pub_path.parent.mkdir(parents=True, exist_ok=True)
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path.write_bytes(pub_bytes)

    print(f"\n{'='*60}")
    print("[RUBICON] KEYPAIR GENERATED")
    print(f"{'='*60}")
    print(f"Private key (OUTSIDE workspace): {priv_path}")
    print(f"Public key  (IN repository):     {pub_path}")
    print(f"\nSet in .env:")
    print(f"  RUBICON_SIGNING_KEY_PATH={priv_path}")
    print(f"\nIMPORTANT: Never commit the private key.")
    print(f"{'='*60}\n")
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    """Show bob_sessions evidence inventory."""
    sessions_dir = _ROOT / "bob_sessions"
    pngs = list(sessions_dir.glob("*.png"))
    print(f"\n{'='*60}")
    print(f"BOB SESSIONS — {len(pngs)} screenshot(s)")
    print(f"{'='*60}")
    if pngs:
        for p in sorted(pngs):
            print(f"  ✓ {p.name}")
    else:
        print("  (none — screenshots must be captured manually from Bob IDE)")
    print(f"\nRequired: task01–task13 session summary PNGs")
    print(f"{'='*60}\n")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="rubicon",
        description="Rubicon — Bob Rollback Effect Boundary Enforcer",
    )
    sub = parser.add_subparsers(dest="command")

    # approve
    p_approve = sub.add_parser("approve", help="Issue a signed permit")
    p_approve.add_argument("--permit-id", dest="permit_id", default="")
    p_approve.add_argument("--action-id", dest="action_id", default="")
    p_approve.add_argument("--session", dest="session", default="")

    # status
    sub.add_parser("status", help="Show session status and pending decisions")

    # receipts
    p_receipts = sub.add_parser("receipts", help="List/display reversibility receipts")
    p_receipts.add_argument("--id", dest="receipt_id", default="")

    # keygen
    p_keygen = sub.add_parser("keygen", help="Generate Ed25519 signing keypair")
    p_keygen.add_argument(
        "--private-key-out",
        dest="private_key_out",
        default=str(Path.home() / ".rubicon" / "rubicon-signer.key"),
        help="Path for private key (OUTSIDE workspace)"
    )

    # sessions
    sub.add_parser("sessions", help="Show bob_sessions evidence inventory")

    args = parser.parse_args()

    if args.command == "approve":
        return cmd_approve(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "receipts":
        return cmd_receipts(args)
    elif args.command == "keygen":
        return cmd_keygen(args)
    elif args.command == "sessions":
        return cmd_sessions(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
