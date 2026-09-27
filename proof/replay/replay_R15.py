"""Replay verification for drill R15 (curl_get_read_only)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R15_receipt.json").read_text())
print(f"Drill R15: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
