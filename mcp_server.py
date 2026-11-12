import json
import sqlite3
from pathlib import Path
import sys

DB_PATH = Path(__file__).parent / "shane.db"

# Copied from agent.py run_sql (Nov 11). Changes: absolute DB path; returns a string.
def run_sql(query):
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return json.dumps([dict(r) for r in rows])
    finally:
        conn.close()

for line in sys.stdin:
    if not line.strip():
        continue
    print(repr(line), file=sys.stderr)  # debug: goes to stderr, never on the wire
    msg = json.loads(line)
    if "id" not in msg:
        continue

    if msg["method"] == "initialize":
        reply = {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "protocolVersion": msg["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fde-sql", "version": "0.1"},
            },
        }
    elif msg["method"] == "tools/list":
        reply = {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "tools": [
                    {
                        "name": "run_sql",
                        "description": "Run a read-only SQL SELECT query against the records-destruction business database and return matching rows. Tables: customer, quote_request, pickups. Only SELECT is permitted; writes and DDL will be rejected.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "A single SQL SELECT statement, SQLite dialect.",
                                }
                            },
                            "required": ["query"],
                        },
                    }
                ]
            },
        }
    elif msg["method"] == "tools/call":
        name = msg["params"]["name"]
        query = msg["params"]["arguments"]["query"]
        try:
            text = run_sql(query)
            is_error = False            
        except sqlite3.Error as e:
            is_error = True
            text = f"tools/call failed: {str(e)}"
        reply = {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "content": [{"type": "text", "text": text}],
                "iserror": is_error,
            },
        }
    else:
        continue


    print(json.dumps(reply), flush=True)
    