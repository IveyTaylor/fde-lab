"""
inspect_response.py -- a read-only tour of what the API actually hands back.

Runs a short scripted conversation (including a tool call) and, at every turn,
prints the response object three ways:

    1. The headline attributes   -- id, model, stop_reason, usage
    2. The content blocks        -- type by type, with the fields each one has
    3. The full raw dump         -- every field, nested, as JSON

Nothing here is part of agent.py. It exists to be read, run once or twice,
and then ignored.

    python inspect_response.py
"""

import json
import os
import sqlite3

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"
DB = "shane.db"

# Set to False once you've seen the raw dumps -- they're long.
SHOW_RAW_DUMP = True


# ---------------------------------------------------------------- the tool

def run_sql(query):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(query).fetchall()]
    finally:
        conn.close()


TOOLS = [
    {
        "name": "run_sql",
        "description": (
            "Run a read-only SQL SELECT query against the records-destruction "
            "business database. Tables: customer, quote_request, pickups."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A SQL SELECT statement."}
            },
            "required": ["query"],
        },
    }
]


# ------------------------------------------------------------ the inspector

def show(response, label):
    """Print one response object three different ways."""

    print()
    print("=" * 70)
    print(f"  {label}")
    print("=" * 70)

    # --- 1. headline attributes -------------------------------------------
    #
    # These live directly on the response object. `usage` is itself an
    # object, which is why it's usage.input_tokens and not usage["input_tokens"].
    #
    print("\n-- top-level attributes --")
    print(f"  type(response)      {type(response).__name__}")
    print(f"  .id                 {response.id}")
    print(f"  .model              {response.model}")
    print(f"  .role               {response.role}")
    print(f"  .stop_reason        {response.stop_reason}")
    print(f"  .stop_sequence      {response.stop_sequence}")
    print(f"  .usage.input_tokens   {response.usage.input_tokens}")
    print(f"  .usage.output_tokens  {response.usage.output_tokens}")

    # --- 2. the content blocks --------------------------------------------
    #
    # response.content is a LIST. Each item is a block, and different block
    # types carry different fields. This is why you branch on block.type
    # instead of reaching for content[0].
    #
    print(f"\n-- .content has {len(response.content)} block(s) --")

    for i, block in enumerate(response.content):
        print(f"\n  [{i}] type = {block.type!r}   ({type(block).__name__})")

        if block.type == "text":
            preview = block.text.strip().replace("\n", " ")
            if len(preview) > 200:
                preview = preview[:200] + " ..."
            print(f"      .text          {preview!r}")

        elif block.type == "tool_use":
            print(f"      .id            {block.id}")
            print(f"      .name          {block.name}")
            print(f"      .input         {block.input}")

        else:
            # Some other block type -- thinking, server_tool_use, etc.
            print(f"      (fields: {list(block.model_dump().keys())})")

    # --- 3. the whole thing -----------------------------------------------
    #
    # model_dump_json is a Pydantic method. Every SDK response object has it.
    # This is the ground truth -- if something isn't printed above, it's here.
    #
    if SHOW_RAW_DUMP:
        print("\n-- raw dump --")
        print(response.model_dump_json(indent=2))


# ------------------------------------------------------------------ the run

def main():
    messages = []

    # ---- turn 1: plain text in, plain text out -------------------------
    #
    # Expect: one content block, type "text", stop_reason "end_turn".
    #
    messages.append({"role": "user", "content": "In one sentence, what is a banker box?"})

    response = client.messages.create(
        model=MODEL, max_tokens=500, tools=TOOLS, messages=messages,
    )
    show(response, "TURN 1  --  simple question, no tool needed")
    messages.append({"role": "assistant", "content": response.content})

    # ---- turn 2: a question that requires the tool ---------------------
    #
    # Expect: stop_reason "tool_use", and possibly TWO blocks -- a text
    # block where the model narrates what it's about to do, followed by
    # the tool_use block itself.
    #
    messages.append({
        "role": "user",
        "content": "How many rows are in the quote_request table? Use the database.",
    })

    response = client.messages.create(
        model=MODEL, max_tokens=500, tools=TOOLS, messages=messages,
    )
    show(response, "TURN 2  --  model wants a tool  (stop_reason should be tool_use)")
    messages.append({"role": "assistant", "content": response.content})

    # ---- run whatever it asked for, and look at the result block -------
    #
    # Note the shape of what WE build: a plain dict, not an SDK object.
    # Requests are dicts you construct; responses are objects the SDK builds.
    #
    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        try:
            output = json.dumps(run_sql(block.input["query"]))
        except Exception as e:
            output = f"SQL error: {e}"
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })

    print("\n-- the tool_result WE construct and send back --")
    print(json.dumps(results, indent=2)[:800])

    messages.append({"role": "user", "content": results})

    # ---- turn 3: model reads the result and answers --------------------
    #
    # Expect: back to stop_reason "end_turn", one text block.
    # Also watch input_tokens -- it jumped, because the whole history plus
    # the tool output is re-sent every single call.
    #
    response = client.messages.create(
        model=MODEL, max_tokens=500, tools=TOOLS, messages=messages,
    )
    show(response, "TURN 3  --  tool result in hand, model answers")
    messages.append({"role": "assistant", "content": response.content})

    # ---- and finally, the transcript ------------------------------------
    #
    # messages is just a list you maintained by hand. Every turn is in it.
    # Roles alternate user / assistant / user / assistant -- note that the
    # tool_result went back as a USER turn, not a third role.
    #
    print()
    print("=" * 70)
    print("  THE MESSAGES LIST YOU BUILT")
    print("=" * 70)
    for i, m in enumerate(messages):
        content = m["content"]
        if isinstance(content, str):
            shape = f"str, {len(content)} chars"
        else:
            kinds = [
                b["type"] if isinstance(b, dict) else b.type
                for b in content
            ]
            shape = f"list of {len(content)} block(s): {kinds}"
        print(f"  [{i}] role={m['role']:<10} content = {shape}")


if __name__ == "__main__":
    main()