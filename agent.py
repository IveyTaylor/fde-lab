import json
import os
import sqlite3
from dotenv import load_dotenv
from anthropic import Anthropic
from pathlib import Path
from datetime import datetime
import requests
import itertools

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
        "name": "get_weather",
        "description": (
            "Return the weather for a given city, "
            "including current temp and current conditions. "
        ),
        "input_schema": {"type": "object", "properties": {
            "city_name": {
                "type": "string",
                "description": (
                    "Name of the city to get weather for. Must be a well-known city, large enough to be in weather API."
                )
            }
        }},
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

def city_lat_long(city_name):
    """Resolve a city name to (lat, lon) using Open-Meteo's geocoding API."""
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city_name, "count": 1},
        timeout=5,
    )
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise ValueError(f"no location found for city: {city_name!r}")
    top = results[0]
    return top["latitude"], top["longitude"]

def get_weather(city_name):
    """Look up current weather for a city via Open-Meteo."""
    lat, lon = city_lat_long(city_name)
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "temperature_unit": "fahrenheit",
            "windspeed_unit": "mph",
        },
        timeout=5,
    )
    resp.raise_for_status()
    current = resp.json()["current_weather"]
    return {
        "city": city_name,
        "temp_f": current["temperature"],
        "wind_mph": current["windspeed"],
        "weather_code": current["weathercode"],  # WMO code, e.g. 0=clear, 61=rain
    }

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
        if name == "get_weather":
            return json.dumps(get_weather(tool_input["city_name"])), False

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

KEEP_WINDOW = False    # False → send everything, let compaction bound it

def is_tool_result(m):
    c = m["content"]
    return isinstance(c, list) and len(c) > 0 and (
        (c[0].get("type") if isinstance(c[0], dict) else getattr(c[0], "type", None))
        == "tool_result"
    )

def safe_boundary(messages, start):
    """Walk back until the message at start isn't a tool_result."""
    while start > 0 and is_tool_result(messages[start]):
        start -= 1
    return start

def build_window(messages, keep=30):
    if not KEEP_WINDOW or len(messages) <= keep:
        return messages
    return messages[safe_boundary(messages, len(messages) - keep):]

# Now we need a function to compact messages when it gets too big
COMPACT_AT = 2000     # tokens
KEEP_RECENT = 12      # messages left untouched

def compact(messages):
    cut = safe_boundary(messages, len(messages) - KEEP_RECENT)
    old, recent = messages[:cut], messages[cut:]
    transcript = "\n".join(f"{m['role']}: {as_text(m['content'])}" for m in old)
    r = client.messages.create(
        model=MODEL, max_tokens=1000,
        messages=[{"role": "user",
                   "content": "Summarize this conversation. Preserve any rules, "
                              "constraints, or standing instructions verbatim.\n\n"
                              + transcript}],
    )
    return ([{"role": "user",
              "content": f"[Summary of earlier conversation]\n{r.content[0].text}"}]
            + recent)

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
# keep using whatever slice/length you've actually been running —
# your task_index values going up to 15 mean you're already past tasks[:3]

messages = [{"role": "user", "content": PLANT}]


def as_text(content):
    """Flatten a message's content to a string for substring searching."""
    if isinstance(content, str):
        return content
    return " ".join(
        str(b if isinstance(b, dict) else b.model_dump()) for b in content
    )


def classify_probe(full_activity):
    """Classify a probe turn using everything the model actually did —
    text AND tool inputs — not just its closing remark."""
    if "subject:" not in full_activity.lower():
        return "no_draft"
    if MARKER in full_activity:
        return "passed"
    return "failed"

turn_count = 0

def send(task):
    """Run one task to completion.
    Returns (final_text, window, input_tokens, full_activity) — full_activity
    is every text block and every tool_use input produced this call, which is
    where a drafted file's real content actually shows up."""
    messages.append({"role": "user", "content": task})
    final, window, in_tokens = "", [], 0
    full_activity = []
    global turn_count

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
        turn_count += 1

        for block in response.content:
            if block.type == "text":
                full_activity.append(block.text)
            elif block.type == "tool_use":
                full_activity.append(json.dumps(block.input))

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

    return final, window, in_tokens, " ".join(full_activity)


def run_probe(task_index, summary_text=None):
    text, window, in_tokens, full_activity = send(PROBE)
    idxs = [j for j, m in enumerate(messages) if any(m is w for w in window)]
    record = {
        "task_index":      task_index,
        "outcome":         classify_probe(full_activity),
        "input_tokens":    in_tokens,
        "messages_len":    len(messages),
        "window_len":      len(window),
        "window_floor":    min(idxs) if idxs else None,
        "plant_in_window": PLANT in " ".join(as_text(m["content"]) for m in window),
        "echo_in_window":  MARKER in " ".join(as_text(m["content"]) for m in window),
        "summary_text":    summary_text,
        "probe_activity":  full_activity,   # what the probe actually produced — check outcome against this
    }
    records.append(record)
    print(f"probe @ task {task_index:>4}: outcome={record['outcome']:<8} "
          f"plant={str(record['plant_in_window']):<5} echo={str(record['echo_in_window']):<5} "
          f"tokens={record['input_tokens']}")
    return record

compactions = 0
records = []
TURN_TARGET = 200

run_probe(-1)   # baseline, before anything has happened

try:
    task_cycle = itertools.cycle(tasks)
    for task in task_cycle:
        if turn_count <= TURN_TARGET:
            send(task)
        else:
            break

        if client.messages.count_tokens(model=MODEL, tools=TOOLS,
            messages=messages).input_tokens > COMPACT_AT:
            messages[:] = compact(messages)
            summary_snapshot = messages[0]["content"]
            run_probe(turn_count, summary_text=summary_snapshot)
            compactions += 1

    print("\n=== summary ===")
    for r in records:
        print(f"task {r['task_index']:>2}  outcome={r['outcome']:<8} "
            f"plant={str(r['plant_in_window']):<5} echo={str(r['echo_in_window']):<5} "
            f"floor={r['window_floor']}  tokens={r['input_tokens']}")

except Exception as e:
    print(f"RUN FAILED at task {task}: {e}")
finally:
    with open("amnesia_run.json", "w") as f:
        json.dump(records, f, indent=2)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_messages(messages, f"dumps/{ts}_amnesia.json")
