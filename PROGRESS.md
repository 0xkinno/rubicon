# PROGRESS.md

Chronological implementation log for RUBICON.

---

## Session 001 — Bootstrap & Setup
**Bob Tasks:** Setup / Pre-Phase-0
- Read and internalized RUBICON_INSTRUCTION.md in full.
- Created full repository directory structure.
- Configured `.gitignore` with `reference/`, `.env`, private keys strictly blocked.
- Created `.env.example` and generated `.env` with IBM watsonx keys.
- Established `rubicon-lab/` disposable lab workspace.
- Implemented core schemas, data models (`core/models.py`), and configuration YAML files (`rollback_contract.yaml`, `rules_registry.yaml`, `policy.yaml`).

---

## Session 002 — Core Engine & Security Hardening
**Bob Tasks:** Task 02, Task 03, Task 04, Task 05
- Implemented deterministic classifier (`core/classifier/classifier.py`) mapping 12 state domains with fail-closed invariant (`UNKNOWN = unsafe`).
- Implemented SQLite mutation regex detection and upgraded compound shell parser to ignore shell operators within quoted strings.
- Implemented Ed25519 one-use permit protocol (`core/permits/permit_engine.py`) with cryptographic action-digest binding.
- Implemented full security attack test suite (`tests/test_security_attacks.py`) covering uppercase bypasses, whitespace evasion, nested subshells, directory traversal, replay attacks, stale permits, and signature tampering.
- 62/62 tests passing cleanly in `pytest`.

---

## Session 003 — Independent Verifier & 21-Drill Benchmark
**Bob Tasks:** Task 06, Task 07, Task 08
- Built independent post-rollback manifest verifier with 6 state adapters (`filesystem`, `git`, `sqlite`, `process`, `http_fixture`, `registry`).
- Implemented 21-drill causal benchmark runner (`scripts/benchmark/run_campaign.py`) testing Arm A (Raw Bob), Arm B (Classifier Gate), and Arm C (Classifier + Verifier).
- Executed campaign generating:
  - 63 SHA-256 pre/post manifests in `proof/manifests/`
  - 21 signed Ed25519 receipts in `proof/receipts/`
  - 21 detached signatures in `proof/signatures/`
  - 21 reproducible replay scripts in `proof/replay/`
- Verified 100.0% classification accuracy (21/21) and zero boundary escapes in Arms B and C.

---

## Session 004 — IBM Bob Sessions & Verification Evidence
**Bob Tasks:** Task 09, Task 10, Task 11, Task 12, Task 13
- Verified all 11 Bob IDE PNG screenshots in `bob_sessions/`.
- Generated detailed audit & review reports in `bob_sessions/shell-logs/` for tasks 12 & 13.
- Populated `bob_sessions/SESSION_LOG.md` with exact session IDs, consumption logs, and 3.566 total Bobcoin usage.
- Ran `scripts/verify/check_bob_sessions.py`: 13/13 items present and valid.

---

## Session 005 — Frontend, Hero Artwork & Playwright Responsive QA
- Generated 16:9 signature Rubicon threshold artwork (`app/web/public/rubicon_hero_art.jpg`).
- Integrated artwork, responsive threshold visualization, live proof cards, and verified campaign metrics into Next.js application.
- Configured FastAPI backend (`app/api/main.py`) serving live decision ledgers, receipts, and health endpoints.
- Executed Playwright Chromium responsive screenshot suite (`scripts/screenshots/playwright_run.py`) capturing all 15 viewports across mobile (375x667, 393x852, 360x800), tablet (768x1024), and desktop (1440x900).
- Confirmed zero horizontal scroll overflow across all 15 responsive viewports.

---

## Session 006 — Competitor Scrubbing & Submission Readiness
- Verified zero competitor mentions exist in public source code, documentation, and UI.
- Initialized clean git repository respecting `.gitignore` with `reference/` fully excluded.
- Updated `README.md`, `PROOF.md`, `EVIDENCE.md`, `DISCOVERY.md`, `LIMITATIONS.md`, `MILESTONE.md`, `docs/CLAIMS.json`, and `TASK.md`.
- All milestones verified 100% complete and submission-ready.
