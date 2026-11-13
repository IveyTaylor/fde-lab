import json
import sqlite3
from pathlib import Path
from mcp.server.mcpserver.exceptions import ToolError
import sys
sys.path.insert(0, str(Path(__file__).parent / "rag"))
import search_hybrid
import search_vector
import requests

from mcp.server.mcpserver import MCPServer

DB_PATH = Path(__file__).parent / "shane.db"
INDEX_PATH = Path(__file__).parent / "rag" / "embeddings_structure.json"

server = MCPServer("fde-lab")
RECORDS = search_vector.load_index(INDEX_PATH)

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

@server.tool()
def search_faa_documents(question: str, source_file: str | None = None) -> str:
    """Search FAA advisory circulars (aviation weather, helicopter safety, altimeter testing, and the AC checklist). 
    Returns the top 5 matching passages as JSON, each with source_file and page range; 
    cite them when answering. Optional source_file limits the search to one document.
    """
    try:
        results = search_hybrid.search(question, RECORDS, source_file=source_file)
    except ValueError as e:
        raise ToolError(str(e)) 
    except requests.exceptions.ConnectionError:
        raise ToolError("The embedding service Ollama isn't running")
    passages = []
    for score, r in results:
        passages.append({"source_file": r["source_file"], 
                         "page_start": r["page_start"], 
                         "page_end": r["page_end"],
                         "text": r["text"]})
    return json.dumps(passages)

if __name__ == "__main__":
    server.run()

