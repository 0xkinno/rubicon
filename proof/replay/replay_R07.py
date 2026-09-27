"""Replay verification for drill R07 (remote_git_push)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R07_receipt.json").read_text())
print(f"Drill R07: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
