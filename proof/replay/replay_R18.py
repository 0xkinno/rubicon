"""Replay verification for drill R18 (read_file)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R18_receipt.json").read_text())
print(f"Drill R18: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
