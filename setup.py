#!/usr/bin/env python3
"""
setup.py — Bootstrap Rubicon without going through Bob's execute_command hook.
Run this directly from the terminal (not from Bob Agent mode).

Usage:
    python setup.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

def run(cmd, cwd=None, check=True):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or ROOT)
    if check and result.returncode != 0:
        print(f"FAILED (exit {result.returncode})")
        sys.exit(result.returncode)
    return result

print("=" * 60)
print("RUBICON SETUP")
print("=" * 60)

# 1. Generate keypair
print("\n[1/3] Generating Ed25519 keypair...")
run(f"python generate_keypair.py")

# 2. Install Python deps
print("\n[2/3] Installing Python dependencies...")
run(f"pip install -r requirements.txt --quiet")

# 3. Install Node deps
print("\n[3/3] Installing frontend dependencies...")
run("npm install --legacy-peer-deps", cwd=ROOT / "app" / "web")

print("\n" + "=" * 60)
print("[RUBICON] SETUP COMPLETE")
print("=" * 60)
print("\nNext steps:")
print("  1. Copy .env.example to .env and set RUBICON_SIGNING_KEY_PATH")
print("  2. Start API:     python -m uvicorn app.api.main:app --port 8000")
print("  3. Start web:     cd app/web && npm run dev")
print("  4. Open:          http://localhost:3000")
print("  5. Run tests:     python -m pytest tests/")
print("  6. Run campaign:  python scripts/benchmark/run_campaign.py")
