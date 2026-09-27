"""Replay verification for drill R10 (process_spawn_background)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R10_receipt.json").read_text())
print(f"Drill R10: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
