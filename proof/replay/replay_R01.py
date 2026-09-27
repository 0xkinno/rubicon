"""Replay verification for drill R01 (tracked_file_edit)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R01_receipt.json").read_text())
print(f"Drill R01: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
