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

USE_SYSTEM = 0

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
QUESTION = "Write a two sentence thank you email to a customer who has had work done over the last 30 days and put it in a file. "
QUESTION = "List every customer who has had a completed pickup in the last 30 days, with the pickup dates."
QUESTION = "Which quote requests from March 2022 to April 2022 have no scheduled pickup?"
QUESTION = "How many quote requests came in last month?, Which customers have never had a pickup?, What's the average box count by service type?"

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

def build_window(messages, keep=30):
    if len(messages) <= keep + 1:
        print(f"{len(messages)} messages of the {keep} messages we are keeping")
        return messages
    print(f"{len(messages)} messages")
    return messages[-keep:]

# This is a cool print I wanted to keep, as it helped me understand stuff
# as seen in OneNote Temp Notes Python
# print(dispatch("write_file", {"file_name": "../stolen", "content": "escaped"}))

# ─────────────────────────── amnesia run ───────────────────────────
MAX_TURNS = 5
MARKER = "Certificate of Destruction"

PLANT = ("Rule for all quotes: hard drive destruction always includes a "
         f"{MARKER} line in the quote email.")
PROBE = "Draft the quote email for a hard drive destruction job."

tasks = [
    "How many quote requests came in last month?",
    "Which customers have never had a pickup?",
    "What's the average box count by service type?",
    "How many boxes were from places called Union something?",
    "What's the price of diesel in California?",
    "How many boxes have we picked up total?",
    "What's our client count by zip code?",
    "Do we have clients in multiple states?",
    "What's the maximum box count by service type?",
    "What's the biggest order we ever did?",
    "What's our best customer?",
    "What's our newest customer?",
    "What's our oldest customer?",
    "What's the weather like in Charlotte right now?",
    "Which customer has the most pickups with null dates?",
]

messages = [{"role": "user", "content": PLANT}]
plant_msg = messages[0]          # identity handle — see note 3


def as_text(content):
    """Flatten a message's content to a string for substring searching."""
    if isinstance(content, str):
        return content
    return " ".join(
        str(b if isinstance(b, dict) else b.model_dump()) for b in content
    )


def send(task):
    """Run one task to completion. Returns (final_text, window, input_tokens)."""
    messages.append({"role": "user", "content": task})
    final, window, in_tokens = "", [], 0

    for _ in range(MAX_TURNS):
        window = build_window(messages)
        params = {
            "model": MODEL,
            "system": SYSTEM if USE_SYSTEM else "",
            "tools": TOOLS,
            "messages": window,
        }
        response = client.messages.create(max_tokens=2000, **params)
        in_tokens = response.usage.input_tokens
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                out, is_error = dispatch(block.name, block.input)        # ← SEAM 1
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": out,
                    "is_error": is_error,
                })
            messages.append({"role": "user", "content": results})
            continue

        final = " ".join(b.text for b in response.content if b.type == "text")
        break

    return final, window, in_tokens


records = []

try:
    for i, task in enumerate(tasks):
        send(task)

        if i % 8 == 0:
            text, window, in_tokens = send(PROBE)
            idxs = [j for j, m in enumerate(messages) if any(m is w for w in window)]
            record = {
                "task_index":     i,
                "passed":         MARKER in text,
                "input_tokens":   in_tokens,
                "messages_len":   len(messages),
                "window_len":     len(window),
                "window_floor":   min(idxs) if idxs else None,
                "plant_in_window": any(m is plant_msg for m in window),
                "echo_in_window":  MARKER in " ".join(as_text(m["content"]) for m in window),
            }
            records.append(record)
            print(record)

    print("\n=== summary ===")
    for r in records:
        print(f"task {r['task_index']:>2}  pass={str(r['passed']):<5} "
            f"plant={str(r['plant_in_window']):<5} echo={str(r['echo_in_window']):<5} "
            f"floor={r['window_floor']}  tokens={r['input_tokens']}")
except Exception as e:
    print(f"RUN FAILED at task {i}: {e}")
finally:
    with open("amnesia_run.json", "w") as f:
        json.dump(records, f, indent=2)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_messages(messages, f"dumps/{ts}_amnesia.json")
