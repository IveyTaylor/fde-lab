import sys
import json

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
        reply = {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "content": [{"type": "text", "text": f"would run: {query}"}],
                "isError": False,
            },
        }
    else:
        continue

    print(json.dumps(reply), flush=True)
    