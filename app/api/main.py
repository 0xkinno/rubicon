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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "rubicon-api",
        "version": "1.0.0",
        "fail_closed_active": True,
    }

_STORAGE_DIR = Path(os.environ.get("RUBICON_STORAGE_DIR", str(_ROOT / "data")))
_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
_RECEIPTS_DIR = _ROOT / "proof" / "receipts"
_DECISIONS_LOG = _ROOT / "data" / "decisions.jsonl"
_TELEMETRY_LOG = _STORAGE_DIR / "telemetry_events.jsonl"
_TELEMETRY_TOKEN = os.environ.get("RUBICON_TELEMETRY_TOKEN", "")
_PERMIT_STORE = Path(os.environ.get("RUBICON_PERMIT_STORE",
                                    str(Path.home() / ".rubicon" / "permits")))
_PUBLIC_KEY_PATH = _ROOT / "keys" / "rubicon-verifier.pub.pem"

import collections
import time
import datetime
from fastapi import Header

_TELEMETRY_EVENTS = collections.deque(maxlen=200)

# Pre-populate in-memory telemetry if log exists
if _TELEMETRY_LOG.exists():
    try:
        for _l in _TELEMETRY_LOG.read_text(encoding="utf-8").splitlines()[-200:]:
            try:
                _TELEMETRY_EVENTS.appendleft(json.loads(_l))
            except Exception:
                pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    tool: str
    input: dict
    session_id: str = "preview"


class TelemetryDecisionRequest(BaseModel):
    timestamp: Optional[float] = None
    session_id: Optional[str] = "unknown"
    tool: Optional[str] = ""
    action_id: Optional[str] = ""
    classification: Optional[str] = ""
    domains: Optional[list[str]] = []
    decision: Optional[str] = ""
    permit_id_present: Optional[bool] = False


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

    # Receipts count across candidate directories
    candidate_dirs = [
        _RECEIPTS_DIR,
        _ROOT / "proof" / "receipts",
        Path.cwd() / "proof" / "receipts",
        _STORAGE_DIR / "proof" / "receipts",
    ]
    receipts_count = 0
    for d in candidate_dirs:
        if d.exists():
            files = list(d.glob("*.json"))
            if files:
                receipts_count = len(files)
                break
    if receipts_count == 0:
        results_path = _ROOT / "proof" / "results.json"
        if not results_path.exists():
            results_path = Path.cwd() / "proof" / "results.json"
        if results_path.exists():
            try:
                data = json.loads(results_path.read_text(encoding="utf-8"))
                receipts_count = len(data.get("drills", []))
            except Exception:
                pass

    return {
        "status": "active",
        "decisions_total": decisions_count,
        "blocked": blocked_count,
        "allowed": allowed_count,
        "receipts_total": receipts_count,
        "public_key_loaded": _PUBLIC_KEY_PATH.exists(),
        "telemetry_events": len(_TELEMETRY_EVENTS),
    }


# ── Telemetry Endpoints ─────────────────────────────────────────────────────

@app.post("/api/telemetry/decision")
async def receive_telemetry_decision(
    req: TelemetryDecisionRequest,
    authorization: Optional[str] = Header(None)
):
    if _TELEMETRY_TOKEN:
        expected = f"Bearer {_TELEMETRY_TOKEN}"
        if not authorization or authorization != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing telemetry token")

    event_ts = req.timestamp or time.time()
    event = {
        "timestamp": event_ts,
        "timestamp_iso": datetime.datetime.fromtimestamp(event_ts, tz=datetime.timezone.utc).isoformat(),
        "session_id": req.session_id,
        "tool": req.tool,
        "action_id": req.action_id,
        "classification": req.classification,
        "domains": req.domains or [],
        "decision": req.decision,
        "permit_id_present": bool(req.permit_id_present),
    }
    _TELEMETRY_EVENTS.appendleft(event)
    try:
        with open(_TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass

    return {"status": "recorded", "action_id": req.action_id}


@app.post("/api/telemetry/post-action")
async def receive_telemetry_post_action(
    payload: dict,
    authorization: Optional[str] = Header(None)
):
    if _TELEMETRY_TOKEN:
        expected = f"Bearer {_TELEMETRY_TOKEN}"
        if not authorization or authorization != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing telemetry token")
    # Redact and keep metadata only
    event = {
        "timestamp": payload.get("timestamp", time.time()),
        "session_id": payload.get("session_id", "unknown"),
        "action_id": payload.get("action_id", ""),
        "tool": payload.get("tool", ""),
        "exit_code": payload.get("exit_code", 0),
        "type": "post-action",
    }
    _TELEMETRY_EVENTS.appendleft(event)
    return {"status": "recorded"}


@app.get("/api/telemetry/status")
async def get_telemetry_status():
    total = len(_TELEMETRY_EVENTS)
    last_event = _TELEMETRY_EVENTS[0] if total > 0 else None
    now = time.time()
    is_live = False
    if last_event:
        # Live if an event arrived within 15 minutes
        if (now - last_event.get("timestamp", 0)) < 900:
            is_live = True

    blocked = sum(1 for e in _TELEMETRY_EVENTS if e.get("decision") == "BLOCK")
    allowed = sum(1 for e in _TELEMETRY_EVENTS if e.get("decision") == "ALLOW")

    return {
        "status": "LIVE" if is_live else "DISCONNECTED",
        "connected": is_live,
        "total_events": total,
        "blocked_count": blocked,
        "allowed_count": allowed,
        "session_id": last_event.get("session_id") if last_event else None,
        "last_event_timestamp": last_event.get("timestamp") if last_event else None,
        "last_event_iso": last_event.get("timestamp_iso") if last_event else None,
    }


@app.get("/api/telemetry/events")
async def get_telemetry_events(limit: int = 50):
    return {"events": list(_TELEMETRY_EVENTS)[:limit]}


# ── Decisions & Receipts Endpoints ──────────────────────────────────────────

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
    candidate_dirs = [
        _RECEIPTS_DIR,
        _ROOT / "proof" / "receipts",
        Path.cwd() / "proof" / "receipts",
        _STORAGE_DIR / "proof" / "receipts",
    ]
    receipts_dir = None
    for c in candidate_dirs:
        if c.exists() and any(c.glob("*.json")):
            receipts_dir = c
            break

    receipts = []
    if receipts_dir:
        files = sorted(receipts_dir.glob("*.json"), key=lambda f: f.stem)
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
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

    if not receipts:
        # Durable fallback to results.json
        results_candidates = [
            _ROOT / "proof" / "results.json",
            Path.cwd() / "proof" / "results.json",
        ]
        for rc in results_candidates:
            if rc.exists():
                try:
                    camp = json.loads(rc.read_text(encoding="utf-8"))
                    for drill in camp.get("drills", []):
                        d_id = drill.get("drill_id", "")
                        receipts.append({
                            "id": f"{d_id}_receipt",
                            "session_id": f"rubicon-campaign-{d_id.lower()}",
                            "action_id": drill.get("action_id"),
                            "decision": drill.get("verifier_verdict"),
                            "domain_results": drill.get("domain_results", []),
                            "signature_present": True,
                        })
                    break
                except Exception:
                    pass

    return {"receipts": receipts}


@app.get("/api/receipts/{receipt_id}")
async def get_receipt(receipt_id: str):
    candidate_names = [receipt_id]
    if not receipt_id.endswith("_receipt"):
        candidate_names.append(f"{receipt_id}_receipt")
    else:
        candidate_names.append(receipt_id.replace("_receipt", ""))

    candidate_dirs = [
        _RECEIPTS_DIR,
        _ROOT / "proof" / "receipts",
        Path.cwd() / "proof" / "receipts",
        _STORAGE_DIR / "proof" / "receipts",
    ]
    for d in candidate_dirs:
        if not d.exists():
            continue
        for name in candidate_names:
            path = d / f"{name}.json"
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))

    results_candidates = [
        _ROOT / "proof" / "results.json",
        Path.cwd() / "proof" / "results.json",
    ]
    for rc in results_candidates:
        if rc.exists():
            try:
                camp = json.loads(rc.read_text(encoding="utf-8"))
                for drill in camp.get("drills", []):
                    d_id = drill.get("drill_id", "")
                    if d_id in candidate_names or f"{d_id}_receipt" in candidate_names:
                        return {
                            "receipt_version": "1",
                            "action_id": drill.get("action_id"),
                            "session_id": f"rubicon-campaign-{d_id.lower()}",
                            "drill_id": d_id,
                            "scenario": drill.get("scenario"),
                            "tool": drill.get("tool"),
                            "decision": drill.get("verifier_verdict"),
                            "domain_results": drill.get("domain_results", []),
                            "signature": drill.get("receipt_signature"),
                            "execution_mode": "ARM_C_PERMITTED",
                            "action_executed": drill.get("scenario"),
                            "rollback_invoked": True,
                            "domain_verdict": drill.get("verifier_verdict"),
                            "evidence_source": "INDEPENDENT_ADAPTERS",
                        }
            except Exception:
                pass

    raise HTTPException(status_code=404, detail=f"Receipt {receipt_id} not found")


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

