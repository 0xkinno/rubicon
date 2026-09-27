# MILESTONE.md

## Milestone 0 — Foundation
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] Repository structure matches RUBICON_INSTRUCTION.md Section 21
- [x] `.gitignore` blocks `reference/`, `.env`, private keys
- [x] All reference materials placed in `reference/` (gitignored)
- [x] `.env.example` present with all required vars
- [x] `TASK.md` created with all phases

---

## Milestone 1 — Phase 0 Discovery Complete
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] R01–R21 experiments run on real Bob instance / lab workspace
- [x] Raw outputs stored in `proof/raw/`
- [x] `DISCOVERY.md` complete — no placeholder fields
- [x] `config/rollback_contract.yaml` locked with VERIFIED states
- [x] Founder-level gate: non-obvious discovery reproduced and proven with SHA-256 manifests

---

## Milestone 2 — Core Engine Deterministic
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] Classifier returns typed `ClassificationResult` for all known tool types
- [x] Rule registry is machine-readable and covers all 12 state domains
- [x] All classifier functions have comprehensive unit/property tests (62/62 tests passing)
- [x] Rollback contract policy is enforced deterministically without AI

---

## Milestone 3 — Bob Enforcement Active
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] `PreToolUse` hook blocks `OUTSIDE_ROLLBACK` and `UNKNOWN_EFFECT` actions
- [x] Permit is one-use, Ed25519-signed, bound to action/session/HEAD
- [x] Forged/stale/self-authored permits fail closed (verified in `tests/test_security_attacks.py`)
- [x] Bob retry from blocked action works end-to-end with permit issuance

---

## Milestone 4 — Independent Verifier Working
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] Baseline, post-action, post-rollback manifests captured deterministically
- [x] All 6 adapters (filesystem, git, sqlite, process, http_fixture, registry) return typed domain results
- [x] Reversibility Receipts produced with Ed25519 signatures
- [x] Multiple `REMAINS_CHANGED` results demonstrated (VCS_REMOTE, DATABASE, PROCESS, EXTERNAL)

---

## Milestone 5 — Proof Campaign Complete
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] 21-drill corpus with R01–R21 executed
- [x] Three-arm (A/B/C) results recorded in `proof/results.json`
- [x] 100.0% classification accuracy (21/21)
- [x] Disclosed honest limitation (Drill R20 `NOT_OBSERVABLE` for unobservable UDP telemetry)
- [x] `docs/CLAIMS.json` populated with all 13 claims VERIFIED

---

## Milestone 6 — UI Product Quality
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] Landing page passes 20-second hero message test with signature threshold artwork
- [x] Operator Dashboard shows real evidence (connected to live FastAPI backend)
- [x] Proof page displays interactive receipt inspector and domain results
- [x] Responsive across all 5 Playwright viewport sizes (375x667, 393x852, 360x800, 768x1024, 1440x900)
- [x] Verified zero console errors and zero horizontal scroll overflow (`overflow: 0px`)

---

## Milestone 7 — Submission Ready
**Status:** ✅ Complete
**Acceptance criteria:**
- [x] 13/13 Bob session evidence artifacts present and verified (`scripts/verify/check_bob_sessions.py`)
- [x] Full security attack test suite passing (`tests/test_security_attacks.py`)
- [x] Competitor mentions 100% scrubbed from public repository and documentation
- [x] All live evidence, manifests, receipts, and signatures cryptographically valid
