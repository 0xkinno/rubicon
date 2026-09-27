# SECURITY.md

## Rubicon Security Model

### Threat model

The primary threat is: an AI agent attempting to self-approve a dangerous action or bypass the rollback boundary check.

Secondary threats:
- Replay of a previously consumed permit
- Forged signature on a permit
- Stale permit used after expiry
- Modified receipt after signing
- Path traversal to escape workspace boundary check
- Shell obfuscation to bypass command classifier
- Self-authored agent approval (writing `{"approved":true}` to a file)

### Permit model

1. **Private key is outside workspace** — Bob's tools cannot access the signing key
2. **Permit is Ed25519-signed** — signature is cryptographically bound to action_id, session_id, tool, normalized action hash, repository identity, current HEAD, and expiry
3. **Permit is one-use** — consumed on first valid use, replay blocked
4. **Permit binding is strict** — every field must match exactly or the permit is rejected
5. **Agent cannot self-sign** — only the human CLI can issue permits

### Fail-closed rules

```
UNKNOWN                        = unsafe → BLOCK
OUTSIDE_ROLLBACK_COVERAGE      = unsafe → BLOCK (unless permitted)
UNOBSERVABLE_EXTERNAL_EFFECT   = unsafe → BLOCK (unless permitted)
MALFORMED_POLICY_INPUT         = unsafe → BLOCK
INVALID_APPROVAL_TOKEN         = unsafe → BLOCK
STALE_APPROVAL_TOKEN           = unsafe → BLOCK
VERIFIER_MISMATCH              = FAIL → receipt verdict BREACH
```

### Classifier bypass attempts and mitigations

| Attack | Mitigation |
|--------|-----------|
| bash -c with opaque content | Classified as UNKNOWN_EFFECT — blocked |
| Path traversal (../../) | Classified as UNKNOWN_EFFECT — blocked |
| Unicode look-alike commands | Normalization before pattern matching |
| Command wrapping (script -c) | Not matched by any safe pattern → UNKNOWN |
| Pipes and redirections | Not unwound statically → UNKNOWN |
| Command substitution $() | Not unwound statically → UNKNOWN |

### Permit bypass attempts and mitigations

| Attack | Mitigation |
|--------|-----------|
| Stale permit | Expiry check at validation time |
| Wrong repo permit | Repository identity field in permit binding |
| Wrong HEAD | HEAD commit hash in permit binding |
| Wrong session | Session ID in permit binding |
| Modified arguments | Normalized action hash in permit binding |
| Replayed permit | One-use: state set to CONSUMED on first use |
| Agent-written JSON approval | Ignored — signature required, not plaintext |
| Corrupted signature | InvalidSignature exception → BLOCK |

### Receipt tampering attempts and mitigations

| Attack | Mitigation |
|--------|-----------|
| Modify manifest after signing | Signature bound to signable_bytes (excludes signature field) |
| Modify result after signing | Signature covers all domain_results |
| Change public key | Public key is committed in repository under keys/ |
| Delete manifest file | Adapter returns NOT_OBSERVABLE — honest limitation |
| Wrong verifier version | verifier_version field in receipt |

### Key handling

- Private key: generated with `python3 cli/rubicon.py keygen`, stored at `~/.rubicon/rubicon-signer.key`
- Public key: committed at `keys/rubicon-verifier.pub.pem`
- Key never appears in environment variables or source code
- `.gitignore` lists `*.pem` with exception for the public key path

### Known limitations

See `LIMITATIONS.md` for the complete honest disclosure.
