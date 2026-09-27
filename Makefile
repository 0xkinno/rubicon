# Makefile — Rubicon build and verification targets
# Usage: make <target>

.PHONY: install test lint clean keygen demo-r07 proof sessions screenshot clean-room

# ─── Setup ────────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt
	cd app/web && npm install

keygen:
	python3 scripts/verify/keygen.py

# ─── Tests ────────────────────────────────────────────────────────────────────

test:
	python3 -m pytest tests/ -v --tb=short

lint:
	python3 -m ruff check core/ cli/ scripts/ tests/ || true
	python3 -m mypy core/ --ignore-missing-imports || true

# ─── Development ──────────────────────────────────────────────────────────────

dev-api:
	cd app/api && uvicorn main:app --reload --port 8000

dev-web:
	cd app/web && npm run dev

# ─── Discovery ────────────────────────────────────────────────────────────────

discovery:
	python3 scripts/discovery/run_experiments.py

# ─── Demo ─────────────────────────────────────────────────────────────────────

demo-r07:
	@echo "=== RUBICON DEMO: R07 — Remote Git Push ==="
	@echo "1. Running classifier on 'git push origin main'..."
	python3 -c "
import sys; sys.path.insert(0,'.')
from core.classifier import Classifier
from pathlib import Path
c = Classifier()
result, v = c.classify('execute_command', {'command': 'git push origin main'}, 'demo-session')
print(f'  ACTION:            git push origin main')
print(f'  DOMAIN:            {v.domains}')
print(f'  ROLLBACK CONTRACT: {v.rollback_contract}')
print(f'  DECISION:          {result.value}')
print(f'  REASON:            {v.reason}')
print(f'  ACTION ID:         {v.action_id[:32]}...')
"

# ─── Proof campaign ───────────────────────────────────────────────────────────

proof:
	python3 scripts/benchmark/run_campaign.py

sessions:
	python3 scripts/verify/check_bob_sessions.py

# ─── Screenshots ──────────────────────────────────────────────────────────────

screenshot:
	python3 scripts/screenshots/playwright_run.py

# ─── Clean-room verification ──────────────────────────────────────────────────
# Runs deterministic proof suite from a clean state.
# Internet not required except for labeled adapter tests.

clean-room:
	@echo "=== RUBICON CLEAN-ROOM VERIFICATION ==="
	python3 -m pytest tests/ -v --tb=short
	python3 scripts/verify/check_bob_sessions.py
	@echo "=== CLEAN-ROOM COMPLETE ==="

# ─── Clean ────────────────────────────────────────────────────────────────────

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
