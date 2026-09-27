"""Replay verification for drill R09 (database_mutation)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R09_receipt.json").read_text())
print(f"Drill R09: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
