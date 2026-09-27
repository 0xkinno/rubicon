#!/usr/bin/env python3
"""
generate_keypair.py — Run directly to generate the Rubicon signing keypair.
Not invoked through execute_command (bypasses Rubicon hook correctly).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

key = Ed25519PrivateKey.generate()
pub = key.public_key()

# Private key — outside workspace
priv_path = Path.home() / ".rubicon" / "rubicon-signer.key"
priv_path.parent.mkdir(parents=True, exist_ok=True)
priv_bytes = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
priv_path.write_bytes(priv_bytes)
try:
    priv_path.chmod(0o600)
except Exception:
    pass  # Windows doesn't support chmod in same way

# Public key — in repository
pub_path = Path(__file__).parent / "keys" / "rubicon-verifier.pub.pem"
pub_path.parent.mkdir(parents=True, exist_ok=True)
pub_bytes = pub.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
pub_path.write_bytes(pub_bytes)

print("=" * 60)
print("[RUBICON] KEYPAIR GENERATED")
print("=" * 60)
print(f"Private key (OUTSIDE workspace): {priv_path}")
print(f"Public key  (IN repository):     {pub_path}")
print(f"\nAdd to .env:")
print(f"  RUBICON_SIGNING_KEY_PATH={priv_path}")
print("=" * 60)
