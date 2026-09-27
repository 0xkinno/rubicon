"""Replay verification for drill R19 (env_write)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R19_receipt.json").read_text())
print(f"Drill R19: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
