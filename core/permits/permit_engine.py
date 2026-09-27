"""
core/permits/permit_engine.py

One-use Ed25519 cryptographic permit protocol.

The private signing key is stored OUTSIDE the workspace.
The hook trusts the signature, never an agent-written field.
Unsigned/malformed/stale/self-authored approvals fail closed.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from core.models import EffectVector, PermitState


# ─────────────────────────────────────────────────────────────────────────────
# Permit data structure
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Permit:
    permit_id: str
    action_id: str
    session_id: str
    tool: str
    normalized_action_hash: str   # SHA256 of normalized action string
    repository_identity: str      # SHA256 of workspace root path
    head_commit: str              # Current HEAD SHA (or "UNKNOWN")
    policy_version: str
    issued_at: float              # Unix timestamp
    expires_at: float             # Unix timestamp
    issuer: str                   # "human" — must never be "agent"
    state: str                    # PermitState
    signature: str = ""           # Ed25519 hex signature

    def to_dict(self) -> dict:
        return asdict(self)

    def signable_bytes(self) -> bytes:
        """Canonical bytes for signing (excludes signature field)."""
        d = self.to_dict()
        d.pop("signature", None)
        d.pop("state", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def binding_matches(
        self,
        action_id: str,
        session_id: str,
        tool: str,
        normalized_action_hash: str,
        repository_identity: str,
        head_commit: str,
    ) -> bool:
        return (
            self.action_id == action_id
            and self.session_id == session_id
            and self.tool == tool
            and self.normalized_action_hash == normalized_action_hash
            and self.repository_identity == repository_identity
            and self.head_commit == head_commit
        )


# ─────────────────────────────────────────────────────────────────────────────
# Permit engine
# ─────────────────────────────────────────────────────────────────────────────

class PermitEngine:
    """
    Issues, validates, and consumes one-use human permits.

    Key management:
      - Private key: loaded from RUBICON_SIGNING_KEY_PATH (outside workspace)
      - Public key: from keys/rubicon-verifier.pub.pem (committed to repo)
    """

    PERMIT_TTL_SECONDS = 300  # 5 minutes
    POLICY_VERSION = os.environ.get("RUBICON_POLICY_VERSION", "1.0.0")

    def __init__(
        self,
        permit_store_dir: Path,
        public_key_path: Path,
        private_key_path: Optional[Path] = None,
    ) -> None:
        self._store = permit_store_dir
        self._store.mkdir(parents=True, exist_ok=True)
        self._pub_key = self._load_public_key(public_key_path)
        self._priv_key: Optional[Ed25519PrivateKey] = None
        if private_key_path and private_key_path.exists():
            self._priv_key = self._load_private_key(private_key_path)

    # ── Key loading ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_public_key(path: Path) -> Ed25519PublicKey:
        with open(path, "rb") as f:
            return serialization.load_pem_public_key(f.read())

    @staticmethod
    def _load_private_key(path: Path) -> Ed25519PrivateKey:
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    # ── Public API ────────────────────────────────────────────────────────────

    def create_pending(self, vector: EffectVector, head_commit: str) -> Permit:
        """
        Create a pending permit record. Does NOT sign yet.
        Call issue_signed() after human review to sign and activate.
        """
        permit = Permit(
            permit_id=str(uuid.uuid4()),
            action_id=vector.action_id,
            session_id=vector.session_id,
            tool=vector.tool,
            normalized_action_hash=hashlib.sha256(
                vector.normalized_action.encode()
            ).hexdigest(),
            repository_identity=hashlib.sha256(
                str(Path.cwd().resolve()).encode()
            ).hexdigest(),
            head_commit=head_commit,
            policy_version=self.POLICY_VERSION,
            issued_at=time.time(),
            expires_at=time.time() + self.PERMIT_TTL_SECONDS,
            issuer="human",
            state=PermitState.PENDING_HUMAN,
        )
        self._save(permit)
        return permit

    def issue_signed(self, permit_id: str) -> Permit:
        """
        Sign and activate a pending permit. Requires private key.
        This is the human approval action.
        """
        if self._priv_key is None:
            raise RuntimeError(
                "Signing key not loaded — cannot issue permit. "
                "Ensure RUBICON_SIGNING_KEY_PATH points to the private key outside workspace."
            )
        permit = self._load(permit_id)
        if permit.state != PermitState.PENDING_HUMAN:
            raise ValueError(f"Permit {permit_id} is not in PENDING_HUMAN state (state={permit.state})")
        if permit.is_expired():
            permit.state = PermitState.EXPIRED
            self._save(permit)
            raise ValueError(f"Permit {permit_id} has expired before signing")

        sig_bytes = self._priv_key.sign(permit.signable_bytes())
        permit.signature = sig_bytes.hex()
        permit.state = PermitState.APPROVED
        self._save(permit)
        return permit

    def validate_and_consume(
        self,
        permit_id: str,
        action_id: str,
        session_id: str,
        tool: str,
        normalized_action: str,
        head_commit: str,
    ) -> tuple[bool, str]:
        """
        Validate a permit against the exact action about to be executed.
        If valid, consume (one-use). Returns (valid: bool, reason: str).
        """
        try:
            permit = self._load(permit_id)
        except FileNotFoundError:
            return False, f"Permit {permit_id} not found — BLOCK"

        # Must be in APPROVED state
        if permit.state == PermitState.CONSUMED:
            return False, "Permit already consumed — replay attack blocked"
        if permit.state == PermitState.EXPIRED:
            return False, "Permit is expired"
        if permit.state != PermitState.APPROVED:
            return False, f"Permit in invalid state: {permit.state}"

        # Check expiry
        if permit.is_expired():
            permit.state = PermitState.EXPIRED
            self._save(permit)
            return False, "Permit expired at validation time"

        # Verify signature
        try:
            self._pub_key.verify(
                bytes.fromhex(permit.signature),
                permit.signable_bytes(),
            )
        except InvalidSignature:
            permit.state = PermitState.FORGED
            self._save(permit)
            return False, "Permit signature invalid — BLOCK (potential tampering)"
        except Exception as exc:
            return False, f"Permit signature verification error: {exc}"

        # Verify binding
        norm_hash = hashlib.sha256(normalized_action.encode()).hexdigest()
        repo_identity = hashlib.sha256(str(Path.cwd().resolve()).encode()).hexdigest()

        if not permit.binding_matches(
            action_id=action_id,
            session_id=session_id,
            tool=tool,
            normalized_action_hash=norm_hash,
            repository_identity=repo_identity,
            head_commit=head_commit,
        ):
            permit.state = PermitState.INVALID
            self._save(permit)
            mismatches = []
            if permit.action_id != action_id: mismatches.append(f"action_id ({permit.action_id} != {action_id})")
            if permit.session_id != session_id: mismatches.append(f"session_id ({permit.session_id} != {session_id})")
            if permit.tool != tool: mismatches.append(f"tool ({permit.tool} != {tool})")
            if permit.normalized_action_hash != norm_hash: mismatches.append(f"norm_hash ({permit.normalized_action_hash} != {norm_hash})")
            if permit.repository_identity != repo_identity: mismatches.append(f"repo_identity ({permit.repository_identity} != {repo_identity})")
            if permit.head_commit != head_commit: mismatches.append(f"head_commit ({permit.head_commit} != {head_commit})")
            return False, f"Permit binding mismatch: {', '.join(mismatches)}"

        # Consume (one-use)
        permit.state = PermitState.CONSUMED
        self._save(permit)
        return True, "Permit valid and consumed"

    def list_pending(self) -> list[Permit]:
        permits = []
        for f in self._store.glob("*.json"):
            try:
                p = self._load(f.stem)
                if p.state == PermitState.PENDING_HUMAN:
                    permits.append(p)
            except Exception:
                pass
        return permits

    # ── Storage ───────────────────────────────────────────────────────────────

    def _save(self, permit: Permit) -> None:
        path = self._store / f"{permit.permit_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(permit.to_dict(), f, indent=2)

    def _load(self, permit_id: str) -> Permit:
        path = self._store / f"{permit_id}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Permit(**data)
