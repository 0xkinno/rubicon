"""Replay verification for drill R12 (npm_publish)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R12_receipt.json").read_text())
print(f"Drill R12: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
