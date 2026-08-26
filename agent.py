import json
import os
import sqlite3
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"

DB = "shane.db"

TOOLS = [
    {
        "name": "run_sql",
        "description": (
            "Run a read-only SQL SELECT query against the records-destruction "
            "business database and return matching rows. "
            "Tables: customer, quote_request, pickups. "
            "Only SELECT is permitted; writes and DDL will be rejected."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A single SQL SELECT statement, SQLite dialect.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_schema",
        "description": (
            "Return the full CREATE TABLE statements for every table in the "
            "database, including column names, types, and constraints. "
            "Call this before writing any query."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
            "name": "get_price_of_fuel",
            "description": (
                "Return the price of diesel fuel for the United States for last week"
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
]

# QUESTION = "Which quote requests from the last 30 days have no scheduled pickup?"
QUESTION = "What was the average price of diesel fuel last week in the US?"

def run_sql(query):
    """Execute a query and return rows as a list of dicts."""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_schema():
    """Return the DDL for every table in the database."""
    rows = run_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return "\n\n".join(r["sql"] for r in rows)

def get_price_of_fuel():
    """This gives the price of diesel fuel for by week."""
    raise ConnectionError("Time out error, please try again")     
    
# Temporary -- confirm the tool works before the model ever calls it.
print(json.dumps(run_sql("SELECT * FROM quote_request LIMIT 3"), indent=2))

messages = [{"role": "user", "content": QUESTION}]

MAX_TURNS = 5

for turn in range(1, MAX_TURNS + 1):
    print(f"\n=== turn {turn} ===")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        tools=TOOLS,
        messages=messages,
    )

    print(f"stop_reason: {response.stop_reason}")
    print(f"response.content.input_tokens: {response.usage.input_tokens}, response.content.output_tokens: {response.usage.output_tokens}")
    # print(f"block_type: {response.content.block.type()}")

    # The model's whole reply goes back into the history, unchanged."for t"
    # response.content is a list of blocks -- append it as-is.
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason != "tool_use":
        # No tool wanted. It's answering. Print the text and stop.
        for block in response.content:
            if block.type == "text":
                print(block.text)
        break

    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue

        print(f"CALL {block.name}: {block.input}")
    
        if block.name == "run_sql":
            try:
                output = json.dumps(run_sql(block.input["query"]))
            except Exception as e:
                output = f"SQL error: {e}"

        elif block.name == "get_schema":
            try:
                output = get_schema()
            except Exception as e:
                output = f"schema error: {e}"

        elif block.name == "get_price_of_fuel":
            try:
                output = get_price_of_fuel()
            except Exception as e:
                output = f"fuel price error: {e}"

        else:
            output = f"unknown tool: {block.name}"
            
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })

    # TODO B: send the results back.
    #   All tool results go in ONE user turn, as a list:
    messages.append({"role": "user", "content": results})

else:
    print(f"hit the {MAX_TURNS}-turn cap without finishing")