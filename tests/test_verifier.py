"""
tests/test_verifier.py

Tests for Rubicon Independent Verifier, Manifest Capture, and Adapters.
Tests cross-domain reconciliation and signed Reversibility Receipts.
"""

import subprocess
import pytest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from core.manifests.manifest import ManifestCapturer
from core.verifier.reconciler import Reconciler
from core.adapters import FilesystemAdapter
from core.models import ReceiptVerdict


@pytest.fixture
def signing_key(tmp_path):
    key = Ed25519PrivateKey.generate()
    key_path = tmp_path / "test_signer.key"
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return key_path


@pytest.fixture
def test_env(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "file1.txt").write_text("initial content 1")
    (workspace / "ignored.txt").write_text("ignored file")
    (workspace / ".gitignore").write_text("ignored.txt\n")

    subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=workspace, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=workspace, capture_output=True)

    return workspace


def test_manifest_capture(test_env):
    capturer = ManifestCapturer(workspace_root=test_env, session_id="test-session-01")
    manifest = capturer.capture(manifest_type="baseline")

    assert manifest.manifest_type == "baseline"
    assert manifest.session_id == "test-session-01"
    assert manifest.workspace_root == str(test_env)
    assert len(manifest.sha256()) == 64


def test_reconciler_restored_domain(test_env, signing_key):
    capturer = ManifestCapturer(workspace_root=test_env, session_id="test-01")

    # 1. Baseline
    pre = capturer.capture(manifest_type="baseline")

    # 2. Modify file
    (test_env / "file1.txt").write_text("MODIFIED")
    post_action = capturer.capture(manifest_type="post_action")

    # 3. Simulate Bob rollback: restore file
    (test_env / "file1.txt").write_text("initial content 1")
    post_rollback = capturer.capture(manifest_type="post_rollback")

    adapters = {
        "WORKSPACE_TRACKED": FilesystemAdapter(workspace_root=test_env),
    }

    reconciler = Reconciler(adapters=adapters, private_key_path=signing_key)
    receipt = reconciler.reconcile(
        pre=pre,
        post_action=post_action,
        post_rollback=post_rollback,
        action_id="act-test-01",
        session_id="test-01",
        affected_domains=["WORKSPACE_TRACKED"],
    )

    assert receipt.action_id == "act-test-01"
    assert receipt.decision == ReceiptVerdict.RESTORED.value
    assert len(receipt.signature) > 0


def test_reconciler_remains_changed_domain(test_env, signing_key):
    capturer = ManifestCapturer(workspace_root=test_env, session_id="test-02")

    # 1. Baseline
    pre = capturer.capture(manifest_type="baseline")

    # 2. Modify tracked file
    (test_env / "file1.txt").write_text("CHANGED UNREVERSIBLE")
    post_action = capturer.capture(manifest_type="post_action")

    # 3. Simulate Bob rollback failure to restore:
    # file1.txt remains changed
    post_rollback = capturer.capture(manifest_type="post_rollback")

    adapters = {
        "WORKSPACE_TRACKED": FilesystemAdapter(workspace_root=test_env),
    }

    reconciler = Reconciler(adapters=adapters, private_key_path=signing_key)
    receipt = reconciler.reconcile(
        pre=pre,
        post_action=post_action,
        post_rollback=post_rollback,
        action_id="act-test-02",
        session_id="test-02",
        affected_domains=["WORKSPACE_TRACKED"],
    )

    assert receipt.decision in (ReceiptVerdict.BREACH.value, ReceiptVerdict.PARTIAL.value)
