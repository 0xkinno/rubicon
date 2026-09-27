"""Replay verification for drill R16 (git_status)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R16_receipt.json").read_text())
print(f"Drill R16: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
