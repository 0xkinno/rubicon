"""Replay verification for drill R14 (path_traversal)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R14_receipt.json").read_text())
print(f"Drill R14: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
