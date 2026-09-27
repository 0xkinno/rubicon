"""
core/verifier/reconciler.py

Post-rollback reconciliation engine.

Compares:
  pre_manifest  →  post_action_manifest  →  post_rollback_manifest

For each affected state domain, returns a typed DomainVerificationResult.
Produces a signed ReversibilityReceipt.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.models import (
    DomainResult,
    DomainVerificationResult,
    ReversibilityReceipt,
    ReceiptVerdict,
    StateDomain,
)
from core.manifests import Manifest


# ─────────────────────────────────────────────────────────────────────────────
# Reconciler
# ─────────────────────────────────────────────────────────────────────────────

class Reconciler:
    """
    Independent post-rollback state reconciler.

    Does NOT rely on Bob's own report of success.
    Each domain is verified independently by its adapter.
    """

    VERIFIER_VERSION = os.environ.get("RUBICON_VERIFIER_VERSION", "1.0.0")
    POLICY_VERSION = os.environ.get("RUBICON_POLICY_VERSION", "1.0.0")

    def __init__(
        self,
        adapters: dict,   # domain → adapter instance
        private_key_path: Optional[Path] = None,
    ) -> None:
        self._adapters = adapters
        self._priv_key: Optional[Ed25519PrivateKey] = None
        if private_key_path and private_key_path.exists():
            with open(private_key_path, "rb") as f:
                self._priv_key = serialization.load_pem_private_key(f.read(), password=None)

    def reconcile(
        self,
        pre: Manifest,
        post_action: Manifest,
        post_rollback: Manifest,
        action_id: str,
        session_id: str,
        affected_domains: list[str],
        execution_mode: str = "ARM_C_PERMITTED",
        action_executed: str = "",
    ) -> ReversibilityReceipt:
        """
        Run full reconciliation and produce a signed receipt.
        """
        domain_results = []
        observability: dict[str, str] = {}

        for domain in affected_domains:
            result = self._reconcile_domain(domain, pre, post_action, post_rollback)
            domain_results.append(result.to_dict())
            observability[domain] = result.result

        verdict = self._compute_verdict(domain_results)
        limitations = self._compute_limitations(domain_results)

        receipt = ReversibilityReceipt(
            receipt_version="1",
            session_id=session_id,
            action_id=action_id,
            policy_version=self.POLICY_VERSION,
            verifier_version=self.VERIFIER_VERSION,
            pre_manifest_sha256=pre.sha256(),
            post_action_manifest_sha256=post_action.sha256(),
            post_rollback_manifest_sha256=post_rollback.sha256(),
            domain_results=domain_results,
            decision=verdict,
            observability=observability,
            limitations=limitations,
            signature="",
            execution_mode=execution_mode,
            action_executed=action_executed,
            rollback_invoked=True,
            baseline_state=pre.sha256(),
            post_action_state=post_action.sha256(),
            post_rollback_state=post_rollback.sha256(),
            domain_verdict=verdict.value if hasattr(verdict, "value") else str(verdict),
            evidence_source="INDEPENDENT_ADAPTERS",
        )

        if self._priv_key:
            sig = self._priv_key.sign(receipt.signable_bytes())
            receipt.signature = sig.hex()

        return receipt

    # ── Domain-level reconciliation ───────────────────────────────────────────

    def _reconcile_domain(
        self,
        domain: str,
        pre: Manifest,
        post_action: Manifest,
        post_rollback: Manifest,
    ) -> DomainResult:
        adapter = self._adapters.get(domain)

        if adapter is None:
            # No adapter — not observable
            return DomainResult(
                domain=domain,
                result=DomainVerificationResult.NOT_OBSERVABLE,
                notes=f"No verifier adapter registered for domain {domain}",
            )

        try:
            pre_hash = adapter.hash_state(pre)
            post_action_hash = adapter.hash_state(post_action)
            post_rollback_hash = adapter.hash_state(post_rollback)
        except Exception as exc:
            return DomainResult(
                domain=domain,
                result=DomainVerificationResult.NOT_OBSERVABLE,
                notes=f"Adapter error: {exc}",
            )

        # Determine result
        if pre_hash == post_rollback_hash:
            if pre_hash != post_action_hash:
                # Action changed it, rollback restored it
                result = DomainVerificationResult.RESTORED
                notes = "State hash matches pre-action baseline after rollback"
            else:
                # Action didn't change it at all
                result = DomainVerificationResult.RESTORED
                notes = "State unchanged throughout (action had no effect on this domain)"
        elif post_action_hash == post_rollback_hash and pre_hash != post_action_hash:
            # Changed by action, NOT restored by rollback
            result = DomainVerificationResult.REMAINS_CHANGED
            notes = f"State changed by action and NOT restored by rollback (pre={pre_hash[:12]}, post={post_rollback_hash[:12]})"
        elif pre_hash == "" and post_action_hash == "" and post_rollback_hash == "":
            result = DomainVerificationResult.NOT_OBSERVABLE
            notes = "Adapter returned empty hashes — domain not observable"
        else:
            result = DomainVerificationResult.CONTRADICTED
            notes = (
                f"Inconsistent state trajectory: "
                f"pre={pre_hash[:12]} → action={post_action_hash[:12]} → rollback={post_rollback_hash[:12]}"
            )

        return DomainResult(
            domain=domain,
            result=result,
            pre_hash=pre_hash,
            post_action_hash=post_action_hash,
            post_rollback_hash=post_rollback_hash,
            notes=notes,
        )

    # ── Verdict computation ───────────────────────────────────────────────────

    @staticmethod
    def _compute_verdict(domain_results: list[dict]) -> str:
        results = [r["result"] for r in domain_results]

        if all(r == DomainVerificationResult.RESTORED for r in results):
            return ReceiptVerdict.RESTORED
        if DomainVerificationResult.REMAINS_CHANGED in results:
            if any(r == DomainVerificationResult.RESTORED for r in results):
                return ReceiptVerdict.PARTIAL
            return ReceiptVerdict.BREACH
        if DomainVerificationResult.NOT_OBSERVABLE in results:
            return ReceiptVerdict.UNKNOWN
        return ReceiptVerdict.UNKNOWN

    @staticmethod
    def _compute_limitations(domain_results: list[dict]) -> list[str]:
        limitations = []
        for r in domain_results:
            if r["result"] == DomainVerificationResult.NOT_OBSERVABLE:
                limitations.append(
                    f"Domain {r['domain']} is not independently observable by Rubicon verifier"
                )
            if r["result"] == DomainVerificationResult.REMAINS_CHANGED:
                limitations.append(
                    f"Domain {r['domain']} was changed by the action and was NOT restored by Bob rollback"
                )
        return limitations
