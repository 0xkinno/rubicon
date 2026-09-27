# RUBICON

[![IBM Bob 2.0 Hackathon](https://img.shields.io/badge/IBM%20Bob-2.0%20Hackathon-0f62fe?style=flat-square)](https://ibm.com)
[![Benchmark](https://img.shields.io/badge/benchmark-21%2F21%20drills%20%7C%20100%25%20verified-brightgreen?style=flat-square)](proof/results.json)
[![Tests](https://img.shields.io/badge/tests-62%20passing-brightgreen?style=flat-square)](tests/)
[![Security](https://img.shields.io/badge/security-Ed25519%20signed-crimson?style=flat-square)](keys/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?style=flat-square)](https://rubicon-platform.vercel.app)

**Developers using IBM Bob in auto-approve mode can unknowingly cross state boundaries that Bob's rollback cannot undo — Rubicon tells them exactly where that line is, and proves what remained after rollback.**

![RUBICON Hero Banner](evidence/responsive/landing_banner.png)

## Live Links

| Resource | Description | Status / Link |
|---|---|---|
| Web Console | Next.js Landing, Dashboard, Proof Console | [rubicon-platform.vercel.app](https://rubicon-platform.vercel.app) |
| Live Dashboard | Boundary Visualizer & Decision Stream | [rubicon-platform.vercel.app/dashboard](https://rubicon-platform.vercel.app/dashboard) |
| Proof Suite | Interactive Reversibility Receipt Inspector | [rubicon-platform.vercel.app/proof](https://rubicon-platform.vercel.app/proof) |
| API Backend | FastAPI Deterministic Engine & Receipt Server | [rubicon-api-ecf2.onrender.com](https://rubicon-api-ecf2.onrender.com) |
| Campaign Results | Machine-readable 21-drill ablation ledger | [`proof/results.json`](proof/results.json) |
| Video Walkthrough | Demonstration of boundary enforcement & verification | [Demo Video Link] |

## Screenshots

| The Rollback Boundary & Assumption | Live Operator Desk |
|:---:|:---:|
| ![The Rollback Boundary](evidence/responsive/shot_threshold.png) | ![Operator Dashboard](evidence/responsive/shot_dashboard.png) |
| **Proof of Effect Boundary & Judge Questions** | **12-Domain Rollback Contract Matrix** |
| ![Proof & Receipts](evidence/responsive/shot_proof.png) | ![Domain Coverage Matrix](evidence/responsive/shot_matrix.png) |

## The Problem

When an IBM Bob agent runs in auto-approve mode, it can execute dozens of tool calls without manual review. Bob's rollback recovers the workspace — but only a bounded subset of what the agent actually changed.

**A workspace can look perfectly clean after rollback while a remote Git ref, a database row, an HTTP event, or a detached process still carries the effect.**

Traditional authorization gates focus on pre-execution: *"Was this command authorized?"* Rubicon establishes the effect governance layer: *"Can this consequence actually be undone, and was every affected state domain independently restored?"*

## The Solution

Rubicon classifies every Bob tool action into one of 12 state domains, determines whether each domain is inside Bob's rollback contract, blocks boundary-crossing actions until a human issues a cryptographic permit, and independently verifies each domain after rollback — issuing a tamper-evident Reversibility Receipt.

## Explore in 2 Minutes

```bash
# 1. Clone and install
git clone <repo> && cd rubicon
pip install -r requirements.txt

# 2. Generate signing keypair (private key stays outside repo)
python3 cli/rubicon.py keygen

# 3. See the classifier in action
python3 -c "
from core.classifier import Classifier
c = Classifier()
result, v = c.classify('execute_command', {'command': 'git push origin main'}, 'demo')
print(f'Classification: {result.value}')
print(f'Domains: {v.domains}')
print(f'Rollback contract: {v.rollback_contract}')
print(f'Decision: {v.decision}')
"

# 4. Run the proof campaign
make proof

# 5. Start the app
make dev-api  # terminal 1
make dev-web  # terminal 2
# Open http://localhost:3000
```

## The Human Workflow

1. Developer enables IBM Bob Agent mode with Rubicon's `PreToolUse` hook configured
2. Bob proposes/executes tool calls automatically
3. For actions touching domains outside the rollback contract (e.g., `git push`, `curl POST`), Rubicon blocks and requests a human permit
4. Developer reviews the action, issues a one-use signed permit via `python3 cli/rubicon.py approve`
5. Bob retries the action — permit is validated and consumed
6. Developer invokes Bob rollback if needed
7. Rubicon independently verifies each state domain and issues a Reversibility Receipt

## How Rubicon Works

### PreToolUse hook

Configured in `.bob/settings.json`. Intercepts every Bob tool call before execution. Classifies the effect vector and either allows, blocks, or blocks-pending-permit.

### Deterministic classifier

Maps 12 state domains against documented Bob rollback coverage. `UNKNOWN = unsafe` — fails closed for all opaque/unresolvable inputs. No AI model involved in reversibility decisions.

### Ed25519 permit protocol

A one-use permit bound to: action digest, session ID, repository identity, current HEAD, tool name, normalized input hash, expiry timestamp, and policy version. The agent cannot self-approve.

### Independent verifier

After Bob rollback, each adapter independently hashes its domain state. The verifier does not trust Bob's self-report. Domains return: `RESTORED | REMAINS_CHANGED | NEVER_COVERED | NOT_OBSERVABLE | CONTRADICTED`.

### Reversibility Receipt

Tamper-evident JSON receipt signed with Ed25519. Public key committed at `keys/rubicon-verifier.pub.pem`. Signature covers all domain results, manifests hashes, and verdict.

## Why This Is Different

| Dimension | Authorization gate tools | RUBICON |
|-----------|--------------------------|---------|
| Primary question | "Was this action authorized?" | "Can this action actually be undone, and was it?" |
| Safety point | Before execution | Before execution **and** after rollback |
| Key evidence | Action authorization | Cross-domain rollback fidelity |
| Main artifact | Decision/refusal | Reversibility Receipt + state manifest |
| Distinctive claim | Agent text has no authority | Rollback success must not be assumed from workspace appearance |

## Demo Evidence

The R07 scenario demonstrates the headline discovery:

```
ACTION:            git push origin main
DOMAIN:            VCS_REMOTE
ROLLBACK CONTRACT: OUTSIDE
DECISION:          BLOCK

[After Bob rollback:]
WORKSPACE:         RESTORED
VCS_REMOTE:        REMAINS_CHANGED
VERDICT:           PARTIAL
PROOF:             SHA256 + ED25519 SIGNATURE
```

> "Rubicon does not tell you that rollback happened. It tells you whether the consequence actually came back."

## Proof / Break Campaign (21-Drill Benchmark)

The 21-drill causal benchmark was executed across 3 ablation arms:
- **Arm A (Baseline - Raw Bob):** Unattended Bob agent execution without Rubicon hooks.
- **Arm B (Rubicon PreToolUse Enforcer):** Fail-closed deterministic classifier + Ed25519 one-use permit fence.
- **Arm C (Rubicon Full Suite):** Enforcer + Post-Rollback Independent Manifest Verifier + Cryptographic Receipts.

### Causal Benchmark Results (`proof/results.json`)

| Metric | Arm A (Raw Bob) | Arm B (Enforcer Only) | Arm C (Full Rubicon) |
|---|---|---|---|
| Total Drills Evaluated (R01–R21) | 21 | 21 | 21 |
| Boundary Escapes Allowed | **14 / 21** (breach) | **0 / 21** (0 escapes) | **0 / 21** (0 escapes) |
| Outside-Rollback Actions Blocked | 0 / 14 (0%) | **14 / 14 (100%)** | **14 / 14 (100%)** |
| Safe Actions Allowed Without Permit | 7 / 7 (100%) | 7 / 7 (100%) | 7 / 7 (100%) |
| Classification Accuracy | N/A | **100.0%** (21/21) | **100.0%** (21/21) |
| State Domains Independently Verified | 0 | 0 | **12 / 12 domains** |
| Ed25519 Signed Reversibility Receipts | 0 | 0 | **21 / 21 signed** |
| Cryptographic Verification Status | N/A | N/A | **21 / 21 PASS (100%)** |
| Deterministic Replay Scripts | N/A | N/A | **21 / 21 generated** |

Full evidence manifests: [`proof/results.json`](proof/results.json), [`proof/campaign.yaml`](proof/campaign.yaml), [`proof/manifests/`](proof/manifests/), and [`proof/receipts/`](proof/receipts/).

Campaign runner: `python scripts/benchmark/run_campaign.py` (or `make proof`)

## Built With

- **IBM Bob IDE** — core integration via lifecycle hooks and rollback
- **Python 3.11+** — deterministic core engine
- **FastAPI** — REST API backend
- **Next.js 14 + TypeScript** — frontend
- **Ed25519 (cryptography library)** — tamper-evident receipts and permits
- **SQLite** — local ledger and proof store
- **Playwright Chromium** — responsive QA and screenshot evidence
- **Framer Motion** — restrained UI animation

## IBM Bob Integration

IBM Bob is a core component of Rubicon, not a claim.

| Bob Primitive | Rubicon Use |
|--------------|------------|
| `PreToolUse` hook | Block dangerous actions before execution; exit code 2 = block |
| `PostToolUse` hook | Record post-execution events; observational only |
| `Stop` hook | Finalize session evidence on Bob session end |
| Bob Rollback | Triggered by user; Rubicon independently verifies all domains after |
| Bob Agent mode | The primary workflow Rubicon enforces |
| `.bob/settings.json` | Rubicon hooks configured here |

Hook configuration: `.bob/settings.json`
Hook implementations: `scripts/hooks/`

## watsonx / Granite Integration

**Optional explainer layer only.**

If `WATSONX_API_KEY` is set, the Granite model translates deterministic receipt data into human-readable incident summaries. The model never decides reversibility, never decides permit validity, and never decides whether evidence is sufficient.

If watsonx credentials are absent, a deterministic fallback summary is generated from the structured receipt data.

**API-deletion test:** Delete watsonx credentials → classifier, permit, verifier, receipts, and benchmark all continue to work unchanged.

## Architecture

```mermaid
flowchart LR
    B[IBM Bob IDE]
    H[PreToolUse Hook]
    C[Deterministic Effect Classifier]
    P[Permit / Policy Engine]
    E[Bob Tool Execution]
    S[Baseline + Post Action Manifest]
    R[Bob Rollback]
    V[Independent Verifier]
    L[Reversibility Ledger]
    G[Granite Explainer]
    W[Web Evidence Console]

    B --> H --> C --> P
    P -->|ALLOW| E
    P -->|BLOCK / PERMIT| B
    E --> S
    S --> R --> V
    V --> L --> W
    L --> G --> W
```

### Effect domain model

```mermaid
flowchart TB
    A[Bob Tool Action] --> EV[Effect Vector]
    EV --> WT[Tracked Workspace]
    EV --> WI[Ignored / Excluded Workspace]
    EV --> VL[Local VCS]
    EV --> VR[Remote VCS]
    EV --> DB[Database]
    EV --> PR[Process Runtime]
    EV --> NW[External Network]
    EV --> UN[Unknown]

    WT --> RB[Rollback Contract]
    WI --> GAP[Coverage Gap]
    VL --> GAP
    VR --> GAP
    DB --> GAP
    PR --> GAP
    NW --> GAP
    UN --> GAP

    GAP --> PF[Permit / Deny]
```

See `docs/ARCHITECTURE.md` for the full architecture.

## Product Flow

```
Bob action → Effect Vector → Rollback Coverage Contract → Permit/Fence
→ Bob Tool Execution → Baseline + Post Action Manifest
→ Bob Rollback → Independent Verifier → Reversibility Ledger
→ Granite Explainer (optional) → Web Evidence Console
```

```text
+-------------------+      +--------------------+      +--------------------+
|  IBM Bob Agent    | ---> |  PreToolUse Hook   | ---> | Deterministic      |
|  Tool Action      |      |  scripts/hooks/    |      | Classifier & Rules |
+-------------------+      +--------------------+      +--------------------+
                                                                |
                                   +----------------------------+----------------------------+
                                   |                                                         |
                            [COVERED_REVERSIBLE]                                    [OUTSIDE_ROLLBACK]
                                   |                                                         |
                                   v                                                         v
                          +--------------------+                                    +--------------------+
                          | Auto-Approve       |                                    | Block Fail-Closed  |
                          | Exit Code 0        |                                    | Exit Code 2        |
                          +--------------------+                                    +--------------------+
                                   |                                                         |
                                   v                                                         v
                          +--------------------+                                    +--------------------+
                          | Workspace Execute  |                                    | Ed25519 Permit     |
                          | & Pre-Manifest     |                                    | Human Verification |
                          +--------------------+                                    +--------------------+
                                   |
                                   v
                          +--------------------+      +--------------------+      +--------------------+
                          | Bob Rollback       | ---> | Independent        | ---> | Signed Ed25519     |
                          | Invoked in IDE     |      | Reconciler Adapters|      | Reversibility      |
                          +--------------------+      +--------------------+      | Receipt            |
                                                                                  +--------------------+
```

## What's New

This is an original Rubicon implementation for the IBM Bob 2.0 Hackathon. Core architectural principles include:
- Evidence-first verification structure
- Deterministic core with AI as optional advisory layer
- API-deletion invariant (core mechanism remains 100% operational offline)
- Clean-room reproduction target with independent verifier and Ed25519 receipts

## Target User

Platform engineers, DevEx teams, security engineers, and engineering leads deploying IBM Bob agents with unattended execution.

## Business Value

- Developer-agent governance without slowing legitimate work
- Verifiable rollback audit trail for incident reviews
- Policy packs per repository for enterprise deployment
- Deterministic proof that an agent's effects were within the stated safety envelope

## Scope and Limitations

See `docs/LIMITATIONS.md` for complete honest disclosure.

Key limitations:
- Opaque shell commands classified as UNKNOWN — blocked by default
- Remote state observable only if adapter can connect at verification time
- Database observation requires known fixture paths
- Bob rollback is invoked by user, not by Rubicon

## Security Model

Rubicon enforces safety through strict cryptographic invariants and zero-trust verification:
- **Fail-Closed by Default (`UNKNOWN = unsafe`)**: Any command whose effect cannot be deterministically proven safe inside the local workspace boundary is blocked immediately (exit code 2).
- **One-Use Nonce-Bounded Permits**: Boundary-crossing actions require human authorization via an Ed25519 cryptographic permit. Each permit is bound to the exact command digest, git commit HEAD, session ID, and timestamp, preventing replay attacks and agent self-approval.
- **Independent Reconciliation**: Rubicon's verifier directly queries underlying operating system, git, database, and network state after rollback rather than trusting agent self-reports.
- **Isolated Key Hierarchy**: Cryptographic signing keys are strictly isolated outside the target repository workspace and never committed to source control.

See `docs/SECURITY.md` for the full threat model and adversarial attack tree.

## Reproduction

```bash
make clean-room
```

Runs unit tests, campaign, receipt verification, and claim validation from a fresh state.

## Roadmap

- CI/agent safety preflight integration for pull request workflows
- Policy pack registry for enterprise multi-repository governance
- Hardware security token (YubiKey/HSM) permit signing adapter
- Hosted multi-tenant evidence and compliance reporting console

## Documentation

| Document | Focus & Description |
|---|---|
| [`PROOF.md`](PROOF.md) | Full 21-drill empirical benchmark results, 3-arm ablation analysis, and statistical safety proofs. |
| [`PROGRESS.md`](PROGRESS.md) | Chronological session engineering ledger documenting phase-by-phase build milestones and verification passes. |
| [`EVIDENCE.md`](EVIDENCE.md) | Verification artifacts inventory, including Bob execution transcripts, state manifests, and receipts. |
| [`DISCOVERY.md`](DISCOVERY.md) | Empirical discovery report analyzing the exact boundary of IBM Bob's rollback contract across 12 domains. |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Comprehensive threat model, security invariants, attack tree analyses, and cryptographic permit specifications. |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Candid operating envelope disclosure, observable state constraints, and failure disclosures. |
| [`docs/CLAIMS.json`](docs/CLAIMS.json) | Machine-readable verification claims ledger mapping test suites, benchmark drills, and reproduction commands. |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production cloud architecture guide for Vercel edge deployment and Render backend hosting. |

## Local Setup

```bash
# Prerequisites: Python 3.11+, Node.js 18+

# 1. Install dependencies
make install

# 2. Generate keypair
python3 cli/rubicon.py keygen

# 3. Copy and fill .env
cp .env.example .env
# Edit: set RUBICON_SIGNING_KEY_PATH

# 4. Start backend
make dev-api

# 5. Start frontend
make dev-web

# 6. Open http://localhost:3000
```

## License

MIT License. See LICENSE.
