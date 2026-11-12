import json
import sqlite3
from pathlib import Path
from mcp.server.mcpserver.exceptions import ToolError
import sys
sys.path.insert(0, str(Path(__file__).parent / "rag"))
import search_hybrid

from mcp.server.mcpserver import MCPServer

DB_PATH = Path(__file__).parent / "shane.db"

server = MCPServer("fde-lab")

@server.tool()
def run_sql(query: str) -> str:
    """Run a read-only SQL SELECT query against the records-destruction business database and return matching rows. Tables: customer, quote_request, pickups. Only SELECT is permitted; writes and DDL will be rejected."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return json.dumps([dict(r) for r in rows])
    except sqlite3.Error as e:
        raise ToolError(str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    server.run()

