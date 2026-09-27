"""Replay verification for drill R21 (git_commit_then_push)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R21_receipt.json").read_text())
print(f"Drill R21: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
