"""
core/policy/policy_engine.py

Blast-Radius Policy Engine for RUBICON.
Enforces role-based permissions over tools, paths, command classes, and state domains.
Follows fail-closed defaults per RUBICON_INSTRUCTION.md Section 13.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "policy.yaml"


class PolicyEngine:
    """Evaluates access decisions against config/policy.yaml."""

    def __init__(self, policy_path: Path | str | None = None) -> None:
        self.policy_path = Path(policy_path) if policy_path else _DEFAULT_POLICY_PATH
        self.policy_data: dict[str, Any] = {}
        self.roles: dict[str, Any] = {}
        self.command_classes: dict[str, Any] = {}
        self.fail_closed_config: dict[str, bool] = {}
        self._load_policy()

    def _load_policy(self) -> None:
        if self.policy_path.exists():
            with open(self.policy_path, "r", encoding="utf-8") as f:
                self.policy_data = yaml.safe_load(f) or {}
            self.roles = self.policy_data.get("roles", {})
            self.command_classes = self.policy_data.get("command_classes", {})
            self.fail_closed_config = self.policy_data.get("fail_closed", {})
        else:
            self.roles = {}
            self.command_classes = {}
            self.fail_closed_config = {"unknown_role": True, "unknown_tool": True}

    def match_command_class(self, command: str) -> list[str]:
        """Return all command classes that match the given command string."""
        matched_classes = []
        clean_cmd = command.strip()
        for cclass_name, cclass_info in self.command_classes.items():
            patterns = cclass_info.get("patterns", [])
            for pattern in patterns:
                try:
                    if re.search(pattern, clean_cmd, re.IGNORECASE):
                        matched_classes.append(cclass_name)
                        break
                except re.error:
                    continue
        return matched_classes

    def evaluate(
        self,
        role: str,
        tool: str,
        path: str | None = None,
        command: str | None = None,
        domains: list[str] | None = None,
    ) -> tuple[bool, str, bool]:
        """
        Evaluate if an action is permitted.
        Returns:
            (allowed: bool, reason: str, requires_permit: bool)
        """
        domains = domains or []

        if role not in self.roles:
            return False, f"Unknown role '{role}' — fail closed", False

        role_info = self.roles[role]
        allows = role_info.get("allow", [])
        boundaries = role_info.get("boundary", [])
        denies = role_info.get("deny", [])

        # Check explicit denies
        for deny_rule in denies:
            deny_tool = deny_rule.get("tool", "")
            if deny_tool == "*" or deny_tool == tool:
                deny_domains = deny_rule.get("domains", [])
                if any(d in deny_domains for d in domains):
                    return False, f"Denied by policy for role '{role}' on domain in {deny_domains}", False

        # Check boundary rules (requires explicit permit)
        for boundary_rule in boundaries:
            b_tool = boundary_rule.get("tool", "")
            if b_tool == "*" or b_tool == tool:
                b_domains = boundary_rule.get("domains", [])
                b_classes = boundary_rule.get("command_class", [])

                if any(d in b_domains for d in domains):
                    return True, f"Boundary action requires permit for role '{role}'", True

                if command and b_classes:
                    matched_classes = self.match_command_class(command)
                    if any(mc in b_classes for mc in matched_classes):
                        return True, f"Boundary command class {b_classes} requires permit for role '{role}'", True

        # Check allow rules
        for allow_rule in allows:
            a_tool = allow_rule.get("tool", "")
            if a_tool == "*" or a_tool == tool:
                # Path check if paths specified
                paths = allow_rule.get("paths", [])
                if paths and path:
                    norm_path = path.replace("\\", "/")
                    path_matched = any(
                        fnmatch.fnmatch(norm_path, p) or fnmatch.fnmatch(Path(norm_path).name, p)
                        for p in paths
                    )
                    if not path_matched:
                        continue

                # Command class check if command_class specified
                c_classes = allow_rule.get("command_class", [])
                if command and c_classes:
                    matched = self.match_command_class(command)
                    if not any(m in c_classes for m in matched):
                        continue

                # Domains check
                a_domains = allow_rule.get("domains", [])
                if a_domains and domains:
                    if not all(d in a_domains for d in domains):
                        continue

                return True, f"Allowed by role '{role}' policy", False

        return False, f"Action not permitted for role '{role}' — fail closed", False
