"""Replay verification for drill R13 (opaque_shell_command)"""
import json
from pathlib import Path
receipt = json.loads(Path(r"C:\Users\hp\Downloads\RUBICON\proof\receipts\R13_receipt.json").read_text())
print(f"Drill R13: Verdict={receipt['decision']} Signature={receipt['signature'][:16]}...")
