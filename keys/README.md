# keys/

This directory holds the Ed25519 **public** key for Rubicon receipt verification.

## `rubicon-verifier.pub.pem`

Committed to the repository. Used to verify signatures on:
- Reversibility Receipts (`proof/receipts/*.json`)
- Permits (`~/.rubicon/permits/*.json`)

## Private key

The private signing key is stored **outside this repository** at the path specified by `RUBICON_SIGNING_KEY_PATH` in `.env`.

Generate the keypair:

```bash
python3 cli/rubicon.py keygen
# or
python3 scripts/verify/keygen.py
```

The keypair is generated with `Ed25519` from the Python `cryptography` library.
