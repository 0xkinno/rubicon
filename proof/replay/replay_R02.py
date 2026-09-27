"""Replay verification for drill R02 (tracked_file_delete_recreate)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R02_receipt.json").read_text())
print(f"Drill R02: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
