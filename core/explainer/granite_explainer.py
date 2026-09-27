"""
core/explainer/granite_explainer.py

IBM watsonx.ai Granite Explainer Layer for RUBICON.
Translates deterministic Reversibility Receipts and Campaign Results into human-readable explanations.
Complies strictly with RUBICON_INSTRUCTION.md Section 22:
- watsonx is an EXPLAINABILITY layer only.
- Never decides reversibility, permits, or verification verdicts.
- Supports deterministic fallback when credentials are absent (API deletion principle).
"""

from __future__ import annotations

import os
from typing import Any, Optional


class GraniteExplainer:
    """Explains deterministic Rubicon receipts and campaign outcomes."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        url: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("WATSONX_API_KEY", "")
        self.project_id = project_id or os.environ.get("WATSONX_PROJECT_ID", "")
        self.url = url or os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_id = model_id or os.environ.get("WATSONX_MODEL_ID", "ibm/granite-13b-instruct-v2")
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        if self.api_key and self.project_id:
            try:
                from ibm_watsonx_ai import Credentials
                from ibm_watsonx_ai.foundation_models import ModelInference

                creds = Credentials(url=self.url, api_key=self.api_key)
                self._client = ModelInference(
                    model_id=self.model_id,
                    credentials=creds,
                    project_id=self.project_id,
                )
            except Exception:
                self._client = None

    def is_available(self) -> bool:
        return self._client is not None

    def explain_receipt(self, receipt: dict[str, Any]) -> str:
        """
        Generate a human-readable explanation of a Reversibility Receipt.
        Falls back deterministically if watsonx is not configured.
        """
        decision = receipt.get("decision", "UNKNOWN")
        action_id = receipt.get("action_id", "unknown")
        domain_results = receipt.get("domain_results", [])
        limitations = receipt.get("limitations", [])

        # Try watsonx if client is configured
        if self._client:
            try:
                prompt = (
                    f"Explain this developer security rollback receipt concisely in 2-3 sentences:\n"
                    f"Action ID: {action_id}\n"
                    f"Verdict: {decision}\n"
                    f"Affected Domains: {[d.get('domain') for d in domain_results]}\n"
                    f"Limitations: {limitations}\n"
                    f"Summary:"
                )
                response = self._client.generate_text(prompt=prompt, params={"max_new_tokens": 120})
                if response and response.strip():
                    return response.strip()
            except Exception:
                pass  # Fall back to deterministic summary

        # Deterministic fallback summary
        return self._deterministic_receipt_summary(receipt)

    def explain_campaign(self, metrics: dict[str, Any]) -> str:
        """
        Generate a summary explanation of the proof campaign metrics.
        """
        total = metrics.get("total_drills", 0)
        outside = metrics.get("outside_rollback_classified", 0)
        unknown = metrics.get("unknown_classified", 0)
        covered = metrics.get("covered_classified", 0)
        accuracy = metrics.get("classification_accuracy", 1.0)

        if self._client:
            try:
                prompt = (
                    f"Summarize these 21-drill security benchmark results for a developer audience in 2 sentences:\n"
                    f"Total Drills: {total}, Accuracy: {accuracy*100:.1f}%, Outside Rollback Caught: {outside}, "
                    f"Fail-Closed Actions: {unknown}, Reversible Actions Allowed: {covered}."
                )
                response = self._client.generate_text(prompt=prompt, params={"max_new_tokens": 120})
                if response and response.strip():
                    return response.strip()
            except Exception:
                pass

        # Deterministic fallback
        return (
            f"Rubicon evaluated {total} security drills with {accuracy*100:.1f}% classification accuracy. "
            f"It identified {outside} actions that lie outside Bob's rollback contract, "
            f"safely allowed {covered} reversible operations, and failed closed on {unknown} opaque/compound commands."
        )

    def _deterministic_receipt_summary(self, receipt: dict[str, Any]) -> str:
        decision = receipt.get("decision", "UNKNOWN")
        action_id = receipt.get("action_id", "unknown")
        domain_results = receipt.get("domain_results", [])
        domains = [d.get("domain", "") for d in domain_results]

        if decision == "RESTORED":
            return (
                f"Action {action_id} was successfully reversed by Bob rollback. "
                f"All affected domains ({', '.join(domains) or 'WORKSPACE_TRACKED'}) "
                f"match their pre-action baseline state."
            )
        elif decision in ("BREACH", "REMAINS_CHANGED"):
            return (
                f"Action {action_id} crossed the Rubicon effect boundary. "
                f"State changes in {', '.join(domains)} remained un-restored after rollback, "
                f"confirming this effect lies outside Bob's automatic workspace recovery."
            )
        elif decision == "PARTIAL":
            return (
                f"Action {action_id} was only partially restored. "
                f"Tracked workspace files were reset, but external state remains modified."
            )
        else:
            return (
                f"Action {action_id} has indeterminate verification status. "
                f"One or more domains ({', '.join(domains)}) are unobservable by local verifiers."
            )
