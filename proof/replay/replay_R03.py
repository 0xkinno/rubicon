"""Replay verification for drill R03 (gitignore_file_mutation)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R03_receipt.json").read_text())
print(f"Drill R03: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
