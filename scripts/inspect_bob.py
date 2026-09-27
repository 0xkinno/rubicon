import sqlite3
import json
import os

db_path = r"C:\Users\hp\AppData\Roaming\IBM Bob\User\globalStorage\state.vscdb"
if not os.path.exists(db_path):
    print("Not found:", db_path)
    exit(0)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT value FROM ItemTable WHERE key = 'IBM.bob-code'")
row = c.fetchone()
if row:
    val = row[0]
    data = json.loads(val.decode('utf-8') if isinstance(val, bytes) else val)
    print("Keys in IBM.bob-code:", list(data.keys()) if isinstance(data, dict) else type(data))
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                print(f"List {k}: len {len(v)}")
                if len(v) > 0 and isinstance(v[0], dict):
                    print("Sample item:", json.dumps(v[0], indent=2)[:300])
            elif isinstance(v, dict):
                print(f"Dict {k}: keys {list(v.keys())[:10]}")
