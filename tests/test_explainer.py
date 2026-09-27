"""
tests/test_explainer.py

Tests for IBM watsonx Granite Explainer layer.
Verifies explainability functionality, deterministic fallback, and API deletion principle.
"""

from core.explainer import GraniteExplainer


def test_explainer_fallback_receipt():
    explainer = GraniteExplainer(api_key="", project_id="")
    receipt = {
        "action_id": "act-test-01",
        "decision": "RESTORED",
        "domain_results": [{"domain": "WORKSPACE_TRACKED", "result": "RESTORED"}],
    }
    explanation = explainer.explain_receipt(receipt)
    assert len(explanation) > 0
    assert "act-test-01" in explanation
    assert "successfully reversed" in explanation


def test_explainer_fallback_breach():
    explainer = GraniteExplainer(api_key="", project_id="")
    receipt = {
        "action_id": "act-push-02",
        "decision": "BREACH",
        "domain_results": [{"domain": "VCS_REMOTE", "result": "REMAINS_CHANGED"}],
    }
    explanation = explainer.explain_receipt(receipt)
    assert len(explanation) > 0
    assert "Rubicon effect boundary" in explanation


def test_explainer_campaign_summary():
    explainer = GraniteExplainer(api_key="", project_id="")
    metrics = {
        "total_drills": 21,
        "outside_rollback_classified": 7,
        "unknown_classified": 5,
        "covered_classified": 7,
        "classification_accuracy": 1.0,
    }
    summary = explainer.explain_campaign(metrics)
    assert "21" in summary
    assert "100.0%" in summary


def test_api_deletion_principle():
    """Verify that deleting credentials does not cause errors or crash the system."""
    explainer = GraniteExplainer(api_key=None, project_id=None)
    assert explainer.is_available() is False
    res = explainer.explain_receipt({"action_id": "a1", "decision": "RESTORED"})
    assert isinstance(res, str)
    assert len(res) > 0
