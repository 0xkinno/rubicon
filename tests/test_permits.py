"""
tests/test_permits.py

Tests for Rubicon One-Use Ed25519 Permit Protocol.
Verifies: issuance, binding checks, one-use enforcement, signature validation,
forgery resistance, and fail-closed security invariants.
"""

import time
import pytest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.permits import PermitEngine
from core.models import EffectVector, PermitState


@pytest.fixture
def keypair(tmp_path):
    priv_key = Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    priv_file = tmp_path / "signer.key"
    pub_file = tmp_path / "verifier.pub.pem"

    priv_bytes = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_file.write_bytes(priv_bytes)
    pub_file.write_bytes(pub_bytes)

    return priv_file, pub_file


@pytest.fixture
def engine(tmp_path, keypair):
    priv_file, pub_file = keypair
    store_dir = tmp_path / "permits"
    return PermitEngine(
        permit_store_dir=store_dir,
        public_key_path=pub_file,
        private_key_path=priv_file,
    )


def _make_vector(action_id="act-12345", session_id="sess-001", tool="execute_command", normalized_action="git push origin main"):
    return EffectVector(
        action_id=action_id,
        session_id=session_id,
        tool=tool,
        normalized_action=normalized_action,
        domains=["VCS_REMOTE"],
        paths=[],
        network_targets=[],
        process_lifetime="none",
        rollback_contract="OUTSIDE",
        decision="OUTSIDE_ROLLBACK",
        reason="Remote push",
        observability="DIRECT_REVERSIBLE",
    )


def test_permit_issuance_and_consumption(engine):
    vector = _make_vector()
    pending = engine.create_pending(vector, head_commit="abcdef0123456789")
    assert len(pending.permit_id) > 10
    assert pending.state == PermitState.PENDING_HUMAN.value

    # Sign it
    signed = engine.issue_signed(pending.permit_id)
    assert signed.state == PermitState.APPROVED.value
    assert len(signed.signature) > 0

    # Validate and consume
    valid, reason = engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id=vector.action_id,
        session_id=vector.session_id,
        tool=vector.tool,
        normalized_action=vector.normalized_action,
        head_commit="abcdef0123456789",
    )
    assert valid is True
    assert "consumed" in reason.lower()

    # Second consumption must FAIL (one-use enforcement)
    valid2, reason2 = engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id=vector.action_id,
        session_id=vector.session_id,
        tool=vector.tool,
        normalized_action=vector.normalized_action,
        head_commit="abcdef0123456789",
    )
    assert valid2 is False
    assert "already" in reason2.lower() or "not in approved state" in reason2.lower()


def test_mismatched_action_fails(engine):
    vector = _make_vector(action_id="act-999")
    pending = engine.create_pending(vector, head_commit="commit-1")
    signed = engine.issue_signed(pending.permit_id)

    valid, reason = engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id="act-tampered",
        session_id=vector.session_id,
        tool=vector.tool,
        normalized_action=vector.normalized_action,
        head_commit="commit-1",
    )
    assert valid is False
    assert "mismatch" in reason.lower()


def test_forged_permit_signature_fails(engine, tmp_path, keypair):
    _, pub_file = keypair

    # Create forged keypair
    forged_priv = Ed25519PrivateKey.generate()
    forged_priv_file = tmp_path / "forged.key"
    forged_priv_file.write_bytes(
        forged_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    forged_engine = PermitEngine(
        permit_store_dir=engine._store,
        public_key_path=pub_file,
        private_key_path=forged_priv_file,
    )

    vector = _make_vector(action_id="act-forged")
    pending = forged_engine.create_pending(vector, head_commit="commit-1")
    signed = forged_engine.issue_signed(pending.permit_id)

    # Legitimate engine validation must reject forged signature
    valid, reason = engine.validate_and_consume(
        permit_id=signed.permit_id,
        action_id=vector.action_id,
        session_id=vector.session_id,
        tool=vector.tool,
        normalized_action=vector.normalized_action,
        head_commit="commit-1",
    )
    assert valid is False
    assert "signature" in reason.lower()
