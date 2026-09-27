"""
tests/test_models.py

Unit tests for Rubicon data models.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from core.models import (
    EffectVector,
    ReversibilityReceipt,
    DomainResult,
    DomainVerificationResult,
    ReceiptVerdict,
    ClassificationResult,
    StateDomain,
)


class TestEffectVector:
    def test_canonical_bytes_deterministic(self):
        v = EffectVector(
            action_id="sha256:abc",
            session_id="sess1",
            tool="execute_command",
            normalized_action="git push origin main",
            domains=["VCS_REMOTE"],
            paths=[],
            network_targets=["origin"],
            process_lifetime="none",
            rollback_contract="OUTSIDE",
            observability="VERIFIABLE",
            decision=ClassificationResult.OUTSIDE_ROLLBACK,
            reason="test",
        )
        b1 = v.canonical_bytes()
        b2 = v.canonical_bytes()
        assert b1 == b2

    def test_domains_sorted_in_canonical_bytes(self):
        v1 = EffectVector(
            action_id="x", session_id="s", tool="t", normalized_action="cmd",
            domains=["VCS_REMOTE", "EXTERNAL_NETWORK"],
            paths=[], network_targets=[], process_lifetime="none",
            rollback_contract="OUTSIDE", observability="VERIFIABLE",
            decision="OUTSIDE_ROLLBACK", reason="r",
        )
        v2 = EffectVector(
            action_id="x", session_id="s", tool="t", normalized_action="cmd",
            domains=["EXTERNAL_NETWORK", "VCS_REMOTE"],
            paths=[], network_targets=[], process_lifetime="none",
            rollback_contract="OUTSIDE", observability="VERIFIABLE",
            decision="OUTSIDE_ROLLBACK", reason="r",
        )
        assert v1.canonical_bytes() == v2.canonical_bytes()

    def test_to_dict_round_trip(self):
        v = EffectVector(
            action_id="sha256:test",
            session_id="s",
            tool="write_file",
            normalized_action="write_file src/app.py",
            domains=["WORKSPACE_TRACKED"],
            paths=["src/app.py"],
            network_targets=[],
            process_lifetime="none",
            rollback_contract="INSIDE",
            observability="VERIFIABLE",
            decision=ClassificationResult.COVERED_REVERSIBLE,
            reason="tracked file",
        )
        d = v.to_dict()
        assert d["tool"] == "write_file"
        assert "WORKSPACE_TRACKED" in d["domains"]


class TestReversibilityReceipt:
    def _make_receipt(self) -> ReversibilityReceipt:
        return ReversibilityReceipt(
            receipt_version="1",
            session_id="sess_test",
            action_id="sha256:abc",
            policy_version="1.0.0",
            verifier_version="1.0.0",
            pre_manifest_sha256="aaa",
            post_action_manifest_sha256="bbb",
            post_rollback_manifest_sha256="aaa",
            domain_results=[{
                "domain": "WORKSPACE_TRACKED",
                "result": DomainVerificationResult.RESTORED,
            }],
            decision=ReceiptVerdict.RESTORED,
            observability={"WORKSPACE_TRACKED": "RESTORED"},
            limitations=[],
            signature="",
        )

    def test_signable_bytes_excludes_signature(self):
        r = self._make_receipt()
        r.signature = "SOME_SIGNATURE"
        b = r.signable_bytes()
        assert b"SOME_SIGNATURE" not in b

    def test_sha256_is_deterministic(self):
        r = self._make_receipt()
        h1 = r.sha256()
        h2 = r.sha256()
        assert h1 == h2
        assert len(h1) == 64

    def test_sha256_changes_with_verdict(self):
        r1 = self._make_receipt()
        r1.decision = ReceiptVerdict.RESTORED
        r2 = self._make_receipt()
        r2.decision = ReceiptVerdict.BREACH
        assert r1.sha256() != r2.sha256()


class TestDomainResult:
    def test_to_dict(self):
        dr = DomainResult(
            domain="VCS_REMOTE",
            result=DomainVerificationResult.REMAINS_CHANGED,
            pre_hash="aaa",
            post_action_hash="bbb",
            post_rollback_hash="bbb",
            notes="Remote state persists after rollback",
        )
        d = dr.to_dict()
        assert d["domain"] == "VCS_REMOTE"
        assert d["result"] == DomainVerificationResult.REMAINS_CHANGED
