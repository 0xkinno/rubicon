"""
app/api/main.py

Rubicon FastAPI backend.

Serves:
  - /api/status           — current session status
  - /api/decisions        — recent decisions from hook log
  - /api/receipts         — list of reversibility receipts
  - /api/receipts/{id}    — single receipt by ID
  - /api/permits/pending  — pending permits awaiting human decision
  - /api/classify         — classify a proposed action (for dashboard preview)
  - /api/health           — health check
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from core.classifier import Classifier
from core.models import ClassificationResult


# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Rubicon API",
    description="Bob Rollback Effect Boundary Enforcer",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.environ.get("NEXT_PUBLIC_RUBICON_API_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_RECEIPTS_DIR = _ROOT / "proof" / "receipts"
_DECISIONS_LOG = _ROOT / "data" / "decisions.jsonl"
_PERMIT_STORE = Path(os.environ.get("RUBICON_PERMIT_STORE",
                                    str(Path.home() / ".rubicon" / "permits")))
_PUBLIC_KEY_PATH = _ROOT / "keys" / "rubicon-verifier.pub.pem"


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    tool: str
    input: dict
    session_id: str = "preview"


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/status")
async def get_status():
    decisions_count = 0
    blocked_count = 0
    allowed_count = 0

    if _DECISIONS_LOG.exists():
        lines = _DECISIONS_LOG.read_text(encoding="utf-8").splitlines()
        decisions_count = len(lines)
        for line in lines:
            try:
                d = json.loads(line)
                if d.get("decision") == "BLOCK":
                    blocked_count += 1
                else:
                    allowed_count += 1
            except Exception:
                pass

    receipts = list(_RECEIPTS_DIR.glob("*.json")) if _RECEIPTS_DIR.exists() else []

    return {
        "status": "active",
        "decisions_total": decisions_count,
        "blocked": blocked_count,
        "allowed": allowed_count,
        "receipts_total": len(receipts),
        "public_key_loaded": _PUBLIC_KEY_PATH.exists(),
    }


@app.get("/api/decisions")
async def get_decisions(limit: int = 50):
    if not _DECISIONS_LOG.exists():
        return {"decisions": []}

    lines = _DECISIONS_LOG.read_text(encoding="utf-8").splitlines()
    decisions = []
    for line in reversed(lines[:limit * 2]):
        try:
            decisions.append(json.loads(line))
            if len(decisions) >= limit:
                break
        except Exception:
            pass

    return {"decisions": decisions}


@app.get("/api/receipts")
async def get_receipts():
    if not _RECEIPTS_DIR.exists():
        return {"receipts": []}

    receipts = []
    for f in sorted(_RECEIPTS_DIR.glob("*.json"), reverse=True)[:20]:
        try:
            data = json.loads(f.read_text())
            receipts.append({
                "id": f.stem,
                "session_id": data.get("session_id"),
                "action_id": data.get("action_id"),
                "decision": data.get("decision"),
                "domain_results": data.get("domain_results", []),
                "signature_present": bool(data.get("signature")),
            })
        except Exception:
            pass

    return {"receipts": receipts}


@app.get("/api/receipts/{receipt_id}")
async def get_receipt(receipt_id: str):
    path = _RECEIPTS_DIR / f"{receipt_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt not found")
    return json.loads(path.read_text())


@app.get("/api/permits/pending")
async def get_pending_permits():
    if not _PUBLIC_KEY_PATH.exists():
        return {"permits": [], "error": "Public key not loaded"}

    try:
        from core.permits import PermitEngine
        engine = PermitEngine(
            permit_store_dir=_PERMIT_STORE,
            public_key_path=_PUBLIC_KEY_PATH,
        )
        pending = engine.list_pending()
        return {
            "permits": [
                {
                    "permit_id": p.permit_id,
                    "action_id": p.action_id,
                    "tool": p.tool,
                    "session_id": p.session_id,
                    "state": p.state,
                    "expires_at": p.expires_at,
                    "is_expired": p.is_expired(),
                }
                for p in pending
            ]
        }
    except Exception as exc:
        return {"permits": [], "error": str(exc)}


@app.post("/api/classify")
async def classify_action(req: ClassifyRequest):
    """Classify a proposed action — for dashboard preview."""
    try:
        classifier = Classifier(workspace_root=_ROOT)
        result, vector = classifier.classify(
            tool=req.tool,
            raw_input=req.input,
            session_id=req.session_id,
        )
        return {
            "classification": result.value,
            "vector": vector.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/campaign")
async def get_campaign():
    """Return proof campaign results."""
    results_path = _ROOT / "proof" / "results.json"
    if not results_path.exists():
        return {"status": "pending", "message": "Campaign not yet run"}
    return json.loads(results_path.read_text())


@app.get("/api/explain/receipt/{receipt_id}")
async def explain_receipt(receipt_id: str):
    """Explain a reversibility receipt using Granite with deterministic fallback."""
    from core.explainer import GraniteExplainer
    path = _RECEIPTS_DIR / f"{receipt_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt not found")
    data = json.loads(path.read_text())
    explainer = GraniteExplainer()
    explanation = explainer.explain_receipt(data)
    return {"receipt_id": receipt_id, "explanation": explanation, "ai_powered": explainer.is_available()}


@app.get("/api/explain/campaign")
async def explain_campaign():
    """Explain campaign metrics using Granite with deterministic fallback."""
    from core.explainer import GraniteExplainer
    results_path = _ROOT / "proof" / "results.json"
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Campaign not yet run")
    data = json.loads(results_path.read_text())
    explainer = GraniteExplainer()
    explanation = explainer.explain_campaign(data.get("metrics", {}))
    return {"explanation": explanation, "ai_powered": explainer.is_available()}

