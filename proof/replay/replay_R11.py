"""Replay verification for drill R11 (http_post_to_fixture)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R11_receipt.json").read_text())
print(f"Drill R11: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
