"""Replay verification for drill R04 (excluded_type_mutation)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R04_receipt.json").read_text())
print(f"Drill R04: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
