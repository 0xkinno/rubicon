"""Replay verification for drill R20 (node_inline_eval)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R20_receipt.json").read_text())
print(f"Drill R20: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
