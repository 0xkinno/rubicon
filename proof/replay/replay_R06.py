"""Replay verification for drill R06 (local_git_commit)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R06_receipt.json").read_text())
print(f"Drill R06: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
