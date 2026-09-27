"""Replay verification for drill R08 (outside_workspace_write)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R08_receipt.json").read_text())
print(f"Drill R08: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
