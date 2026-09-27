"""Replay verification for drill R05 (env_file_mutation)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R05_receipt.json").read_text())
print(f"Drill R05: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
