#!/usr/bin/env python3
"""
scripts/verify/keygen.py

Generate Ed25519 keypair for Rubicon permit signing.
Private key must be stored OUTSIDE the workspace.
Public key is committed to the repository under keys/.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))


def main() -> None:
    sys.argv = [sys.argv[0], "keygen"]
    from cli.rubicon import cmd_keygen
    import argparse
    args = argparse.Namespace(
        private_key_out=str(Path.home() / ".rubicon" / "rubicon-signer.key")
    )
    sys.exit(cmd_keygen(args))


if __name__ == "__main__":
    main()
