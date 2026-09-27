# LIMITATIONS.md

## Rubicon Operating Envelope and Honest Limitations

This document discloses exactly what Rubicon cannot do. A disclosed limitation is stronger than a false claim of omniscience.

---

### 1. Classifier cannot resolve opaque shell content (Drill R21)

When a command uses `sh -c "..."`, `bash -c "..."`, `powershell -Command "..."`, `node -e "..."`, or similar patterns with runtime-constructed content, Rubicon cannot statically determine the transitive effect. These are classified as `UNKNOWN_EFFECT` and blocked fail-closed.

**Consequence:** Legitimate but complex shell pipelines require explicit human permit issuance.

---

### 2. Compound commands are opaque to static analysis

Commands using `&&`, `||`, `;`, `|` (pipes), or `$()` (command substitution) may involve effects across multiple domains. Rubicon classifies the overall command as `UNKNOWN_EFFECT` unless every component sub-command can be statically resolved.

---

### 3. Remote state is observable only if the adapter can connect

The Git adapter calls `git ls-remote origin` to observe remote refs. If the remote network endpoint is not accessible at verification time, the domain result is `NOT_OBSERVABLE`. Rubicon correctly discloses this — it never fabricates verification results it cannot observe.

---

### 4. Database state in gitignored paths

SQLite databases in `.gitignore`-matched paths are excluded from Bob rollback. The SQLite adapter detects mutations for configured databases in `db/`. Databases written to arbitrary unexpected paths outside registered locations return `NOT_OBSERVABLE`.

---

### 5. Process persistence checking requires process observation

The process adapter uses process inspection to detect persistent daemon children. If process introspection is restricted by OS container policies, process snapshots are unavailable and the domain returns `NOT_OBSERVABLE`.

---

### 6. Permit expiry relies on local system time

Permit validity timestamps use monotonic/system epoch timestamps. If system clocks are deliberately manipulated in an untrusted host, stale permits could appear temporally valid unless explicitly revoked.

---

### 7. Verifier does not observe arbitrary external third-party network mutations (Drill R20)

In Drill R20 (`unobservable_external_side_effect`), Rubicon's verifier reports `NOT_OBSERVABLE`. Controlled local endpoints (HTTP fixture adapter) can be probed before and after, but external non-queryable network targets (third-party webhooks, UDP packets) cannot be read back. Rubicon discloses this honestly.

---

### 8. Bob rollback execution is invoked by the human / IDE, not by Rubicon

Rubicon does not emulate Bob rollback in code. The actual rollback is executed by IBM Bob IDE. Rubicon captures the pre-action and post-rollback manifests to independently verify whether the rollback actually succeeded across each state domain.

---

### 9. Multi-agent / concurrent task interactions

For concurrent Bob tasks editing overlapping files (R13/R14-type scenarios), manifest comparison detects concurrent mutation as `CONTRADICTED` or `PARTIAL`. Rubicon flags this boundary condition clearly.
