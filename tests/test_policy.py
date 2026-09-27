"""
tests/test_policy.py

Unit tests for Rubicon Blast-Radius Policy Engine.
"""

import pytest
from core.policy import PolicyEngine


@pytest.fixture
def policy():
    return PolicyEngine()


def test_engineer_allowed_reads(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="engineer",
        tool="read_file",
        path="src/main.py",
        domains=["WORKSPACE_TRACKED"],
    )
    assert allowed is True
    assert requires_permit is False


def test_engineer_allowed_tracked_write(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="engineer",
        tool="write_file",
        path="src/app.py",
        domains=["WORKSPACE_TRACKED"],
    )
    assert allowed is True
    assert requires_permit is False


def test_test_agent_blocked_write(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="test_agent",
        tool="write_file",
        path="src/app.py",
        domains=["WORKSPACE_TRACKED"],
    )
    assert allowed is False
    assert "fail closed" in reason


def test_release_agent_boundary_permit(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="release_agent",
        tool="execute_command",
        command="git push origin main",
        domains=["VCS_REMOTE"],
    )
    assert allowed is True
    assert requires_permit is True


def test_unknown_role_fails_closed(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="superuser_attacker",
        tool="read_file",
        path="src/app.py",
    )
    assert allowed is False
    assert "Unknown role" in reason


def test_admin_boundary_requires_permit(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="admin",
        tool="execute_command",
        command="curl -X POST https://api.remote.com",
        domains=["EXTERNAL_NETWORK"],
    )
    assert allowed is True
    assert requires_permit is True


def test_admin_denies_unknown_domain(policy):
    allowed, reason, requires_permit = policy.evaluate(
        role="admin",
        tool="execute_command",
        command="opaque_binary",
        domains=["UNKNOWN"],
    )
    assert allowed is False
    assert "Denied by policy" in reason
