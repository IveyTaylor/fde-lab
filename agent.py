import json
import os
import sqlite3
from dotenv import load_dotenv
from anthropic import Anthropic
from pathlib import Path
from datetime import datetime

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"
DB = "shane.db"
WORKSPACE = Path("workspace").resolve()
SYSTEM = (
"You are a quoting assistant for a records-destruction business. "
"You have read-only database access, a fuel price lookup, and a workspace "
"for reading and writing files. Answer from data you retrieve, not from "
"assumption — if you don't know a schema, call get_schema before querying."
)    

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
    {
        "name": "read_file",
        "description": (
            "Read a text file from the agent's workspace directory and return "
            "its contents, up to the first 5000 characters. Files outside the "
            "workspace cannot be accessed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": (
                        "Name of the file to read, relative to the workspace "
                        "directory. Must not contain path separators or '..'."
                    ),
                }
            },
            "required": ["file_name"],
        },
    },
     {
        "name": "write_file",
        "description": (
            "Write text to a file in the agent's workspace directory. "
            "If the file already exists it is overwritten without warning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": (
                        "Name of the file to write, relative to the workspace "
                        "directory. Must not contain path separators or '..'."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "The full text to write to the file.",
                },
            },
            "required": ["file_name", "content"],
        },
    },
]

# I can do this because each question overwrites the previous value
QUESTION = "What was the average price of diesel fuel last week in the US?"
QUESTION = "Which quote requests from March 2022 to April 2022 have no scheduled pickup?"
QUESTION = "Write a two sentence thank you email to a customer who has had work done over the last 30 days and put it in a file. "
QUESTION = "List every customer who has had a completed pickup in the last 30 days, with the pickup dates."

def write_file(file_name, content):
    target = (WORKSPACE / file_name).resolve()
    if not target.is_relative_to(WORKSPACE):
        raise PermissionError(
            f"file access is limited to the workspace directory: {file_name}"
        )
    target = target.with_suffix(".txt")
    target.write_text(content)
    return f"Wrote {len(content)} characters to a file called {file_name}"        

def read_file(file_name):
    target = (WORKSPACE / file_name).resolve()
    if not target.is_relative_to(WORKSPACE):
        raise PermissionError(
            f"file access is limited to the workspace directory: {file_name}"
        )

    size = target.stat().st_size
    text = target.read_text()[:5000]
    if size > 5000:
        text += f"\n\n[Truncated. File is {size} bytes; showing the first 5000 characters.]"
    return text

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

def dispatch(name, tool_input):
    try:
        if name == "run_sql":
            return json.dumps(run_sql(tool_input["query"])), False

        elif name == "get_schema":
            return get_schema(), False

        elif name == "get_price_of_fuel":
            return get_price_of_fuel(), False

        elif name == "read_file":
            return read_file(tool_input["file_name"]), False
        
        elif name == "write_file":
            result = write_file(
                file_name=tool_input["file_name"], 
                content=tool_input["content"])
            return result, False

        else:
            return f"unknown tool: {name}", True

    except Exception as e:
        return f"{name} failed: {e}", True

def dump_messages(messages, path="messages_dump.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    def clean(m):
        content = m["content"]
        if isinstance(content, list):
            content = [
                b.model_dump() if hasattr(b, "model_dump") else b
                for b in content
            ]
        return {"role": m["role"], "content": content}

    Path(path).write_text(
        json.dumps([clean(m) for m in messages], indent=2, default=str)
    )

def build_window(messages):
    window = messages[0:1] + messages[-2:]
    return window

# This is a cool print I wanted to keep, as it helped me understand stuff
# as seen in OneNote Temp Notes Python
# print(dispatch("write_file", {"file_name": "../stolen", "content": "escaped"}))
messages = [{"role": "user", "content": QUESTION}]

MAX_TURNS = 5

for turn in range(1, MAX_TURNS + 1):
    print(f"\n=== turn {turn} ===")
    window = build_window(messages)

    print(f"\n count of tokens: {client.messages.count_tokens(
        model=MODEL,
        messages=window,
        tools=TOOLS,
          )}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        tools=TOOLS,
        messages=window,
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
        dump_messages(messages, f"dumps/{datetime.now():%H%M%S}_finished.json")
        break

    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue

        print(f"CALL {block.name}: {block.input}")

        output, is_error = dispatch(block.name, block.input)
                    
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
            "is_error": is_error,
        })

    # TODO B: send the results back.
    #   All tool results go in ONE user turn, as a list:
    messages.append({"role": "user", "content": results})

else:
    print(f"hit the {MAX_TURNS}-turn cap without finishing")
    dump_messages(messages, f"dumps/{datetime.now():%H%M%S}_capped.json")