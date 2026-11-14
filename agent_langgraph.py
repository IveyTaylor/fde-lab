"""Phase 4: the Phase 1 agent rebuilt in LangGraph.

agent.py stays frozen as the by-hand baseline. This file does the same job
(question -> tool calls -> answer) with the framework running the loop.
"""
import json
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain.agents import create_agent

load_dotenv()  # reads ANTHROPIC_API_KEY from .env, same as agent.py

MODEL = "claude-haiku-4-5-20251001"  # same model as agent.py, so the comparison is fair
DB_PATH = Path(__file__).parent / "shane.db"
SYSTEM = (
    "You are a quoting assistant for a records-destruction business. "
    "You have read-only database access. Answer from data you retrieve, not from "
    "assumption. If you don't know a schema, call get_schema before querying."
)


@tool
def run_sql(query: str) -> str:
    """Run a read-only SQL SELECT query against the records-destruction business database and return matching rows. Tables: customer, quote_request, pickups. Only SELECT is permitted; writes and DDL will be rejected."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return json.dumps([dict(r) for r in rows])
    except sqlite3.Error as e:
        return f"run_sql failed: {e}"
    finally:
        conn.close()


@tool
def get_schema() -> str:
    """Return the full CREATE TABLE statements for every table in the database, including column names, types, and constraints. Call this before writing any query."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return "\n\n".join(r[0] for r in rows)
    finally:
        conn.close()


def build_agent(model=None):
    model = model or ChatAnthropic(model=MODEL, max_tokens=2000)
    return create_agent(model, tools=[run_sql, get_schema], system_prompt=SYSTEM)


def ask(agent, question):
    """Run one question to completion and print every step the framework took."""
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    for m in result["messages"]:
        if m.type == "ai" and m.tool_calls:
            for call in m.tool_calls:
                print(f"[tool_call] {call['name']} {call['args']}", file=sys.stderr)
        elif m.type == "tool":
            print(f"[tool_result] {m.name}: {str(m.content)[:200]}", file=sys.stderr)
    return result["messages"][-1].text


if __name__ == "__main__":
    question = "Which customers have never had a pickup?"
    print(ask(build_agent(), question))
    