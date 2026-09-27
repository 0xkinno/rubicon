"""Replay verification for drill R17 (npm_test)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R17_receipt.json").read_text())
print(f"Drill R17: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
