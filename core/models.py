"""
core/models.py — Shared typed data models for Rubicon core engine.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# State domain enum
# ─────────────────────────────────────────────────────────────────────────────

class StateDomain(str, Enum):
    WORKSPACE_TRACKED = "WORKSPACE_TRACKED"
    WORKSPACE_IGNORED = "WORKSPACE_IGNORED"
    WORKSPACE_EXCLUDED = "WORKSPACE_EXCLUDED"
    VCS_LOCAL = "VCS_LOCAL"
    VCS_REMOTE = "VCS_REMOTE"
    PACKAGE_REGISTRY = "PACKAGE_REGISTRY"
    EXTERNAL_NETWORK = "EXTERNAL_NETWORK"
    PROCESS_RUNTIME = "PROCESS_RUNTIME"
    OUTSIDE_WORKSPACE = "OUTSIDE_WORKSPACE"
    DATABASE_STATE = "DATABASE_STATE"
    CREDENTIAL_STATE = "CREDENTIAL_STATE"
    UNKNOWN = "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Classification result enum
# ─────────────────────────────────────────────────────────────────────────────

class ClassificationResult(str, Enum):
    COVERED_REVERSIBLE = "COVERED_REVERSIBLE"
    BOUNDARY_REQUIRES_PERMIT = "BOUNDARY_REQUIRES_PERMIT"
    OUTSIDE_ROLLBACK = "OUTSIDE_ROLLBACK"
    UNKNOWN_EFFECT = "UNKNOWN_EFFECT"
    UNOBSERVABLE_EFFECT = "UNOBSERVABLE_EFFECT"
    DENY_POLICY = "DENY_POLICY"


# ─────────────────────────────────────────────────────────────────────────────
# Permit state enum
# ─────────────────────────────────────────────────────────────────────────────

class PermitState(str, Enum):
    PROPOSED = "PROPOSED"
    CLASSIFIED = "CLASSIFIED"
    PENDING_HUMAN = "PENDING_HUMAN"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    FORGED = "FORGED"
    INVALID = "INVALID"


# ─────────────────────────────────────────────────────────────────────────────
# Enforcement decision enum
# ─────────────────────────────────────────────────────────────────────────────

class EnforcementDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    BLOCK_PENDING_PERMIT = "BLOCK_PENDING_PERMIT"
    DENY = "DENY"


# ─────────────────────────────────────────────────────────────────────────────
# Domain verification result enum
# ─────────────────────────────────────────────────────────────────────────────

class DomainVerificationResult(str, Enum):
    RESTORED = "RESTORED"
    REMAINS_CHANGED = "REMAINS_CHANGED"
    NEVER_COVERED = "NEVER_COVERED"
    NOT_OBSERVABLE = "NOT_OBSERVABLE"
    CONTRADICTED = "CONTRADICTED"


# ─────────────────────────────────────────────────────────────────────────────
# Receipt verdict enum
# ─────────────────────────────────────────────────────────────────────────────

class ReceiptVerdict(str, Enum):
    RESTORED = "RESTORED"
    PARTIAL = "PARTIAL"
    BREACH = "BREACH"
    UNKNOWN = "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Effect vector
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EffectVector:
    action_id: str
    session_id: str
    tool: str
    normalized_action: str
    domains: list[str]
    paths: list[str]
    network_targets: list[str]
    process_lifetime: str  # "none" | "ephemeral" | "persistent"
    rollback_contract: str  # "INSIDE" | "OUTSIDE" | "PARTIAL" | "UNKNOWN"
    observability: str      # "VERIFIABLE" | "PARTIAL" | "NOT_OBSERVABLE"
    decision: str
    reason: str
    raw_input: Optional[dict] = field(default=None)

    def to_dict(self) -> dict:
        return asdict(self)

    def canonical_bytes(self) -> bytes:
        """Canonical deterministic bytes for signing/hashing."""
        canonical = {
            "action_id": self.action_id,
            "session_id": self.session_id,
            "tool": self.tool,
            "normalized_action": self.normalized_action,
            "domains": sorted(self.domains),
            "paths": sorted(self.paths),
            "network_targets": sorted(self.network_targets),
            "process_lifetime": self.process_lifetime,
            "rollback_contract": self.rollback_contract,
            "decision": self.decision,
        }
        return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()


# ─────────────────────────────────────────────────────────────────────────────
# Domain result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DomainResult:
    domain: str
    result: str  # DomainVerificationResult
    pre_hash: Optional[str] = None
    post_action_hash: Optional[str] = None
    post_rollback_hash: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Reversibility Receipt
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReversibilityReceipt:
    receipt_version: str
    session_id: str
    action_id: str
    policy_version: str
    verifier_version: str
    pre_manifest_sha256: str
    post_action_manifest_sha256: str
    post_rollback_manifest_sha256: str
    domain_results: list[dict]
    decision: str  # ReceiptVerdict
    observability: dict
    limitations: list[str]
    signature: str = ""  # Ed25519 hex, filled after signing

    def to_dict(self) -> dict:
        return asdict(self)

    def signable_bytes(self) -> bytes:
        """Bytes to sign: everything except the signature field itself."""
        d = self.to_dict()
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def sha256(self) -> str:
        return hashlib.sha256(self.signable_bytes()).hexdigest()
