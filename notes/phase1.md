# Phase 1 — The agent loop, by hand

**Week 2 · Aug 24–28, 2026 · Gate Aug 30**
Deliverable: agent with 3+ heterogeneous tools completing a multi-step task unattended.

---

## Aug 24–25 — A SQL tool with no schema tool burns money on metadata

When you use a SQL query function as a tool, you can waste a lot of money pulling
`SELECT * FROM tblA` just to get the metadata of a table.

I used up six turns by asking it to pull data from 3 tables without any schema help:

```
python agent.py
=== turn 1 ===
stop_reason: tool_use
CALL run_sql: {'query': "\nSELECT qr.*, c.company_name\nFROM quote_request qr\nLEFT JOIN customer c ON qr.customer_id = c.customer_id\nLEFT JOIN pickups p ON qr.quote_request_id = p.quote_request_id\nWHERE qr.created_date >= date('now', '-30 days')\nAND p.pickup_id IS NULL\nORDER BY qr.created_date DESC\n"}

=== turn 2 ===
stop_reason: tool_use
CALL run_sql: {'query': "\nSELECT qr.*\nFROM quote_request qr\nLEFT JOIN pickups p ON qr.quote_request_id = p.quote_request_id\nWHERE qr.created_date >= date('now', '-30 days')\nAND p.pickup_id IS NULL\nORDER BY qr.created_date DESC\n"}

=== turn 3 ===
stop_reason: tool_use
CALL run_sql: {'query': '\nSELECT * FROM quote_request LIMIT 1\n'}

=== turn 4 ===
stop_reason: tool_use
CALL run_sql: {'query': '\nSELECT * FROM pickups LIMIT 1\n'}

=== turn 5 ===
stop_reason: tool_use
CALL run_sql: {'query': "\nSELECT qr.quote_request_id, qr.customer_id, qr.quote_request_contact, qr.service_type, qr.box_count, qr.volume_stated_as, qr.urgency, qr.create_date\nFROM quote_request qr\nLEFT JOIN pickups p ON qr.quote_request_id = p.quote_request_id\nWHERE qr.create_date >= date('now', '-30 days')\nAND p.pickup_id IS NULL\nORDER BY qr.create_date DESC\n"}

=== turn 6 ===
stop_reason: end_turn
Based on the query results, here are the **5 quote requests from the last 30 days that have no scheduled pickup**:

| Quote Request ID | Customer ID | Contact | Service Type | Box Count | Volume | Urgency | Create Date |
|---|---|---|---|---|---|---|---|
| 15 | 6 | Bettina Salas | Shredding | 8 | Eight boxes | Flexible | 2026-08-23 |
| 14 | (none) | (none) | Hard drive destruction | (none) | Old computers from the remodel | (none) | 2026-08-20 |
| 13 | 2 | Reg Alameda | Scanning | (none) | Not sure yet, still sorting | (none) | 2026-08-14 |
| 12 | (none) | Kelly | Shredding | 30 | About 30 boxes | ASAP | 2026-08-07 |
| 11 | (none) | Front desk | Shredding | (none) | A few boxes, maybe more once we get into the back closet | (none) | 2026-07-29 |

The most recent unscheduled quote request is #15 (Bettina Salas, shredding, 8 boxes), and notably quote request #12 (Kelly) is marked as ASAP but has no pickup scheduled yet.
(.venv)
pktiv@LAPTOP-MLKBJBL7 MINGW64 ~/fde-lab (main)
$
```

Note: turns 1 and 2 failed on `created_date` vs `create_date` — the model guessed a
column name and got it wrong twice before falling back to discovery.

---

## Aug 25 — get_schema: 6 turns → 3 turns

Agent with three table names in the tool description: 6 turns, 5 API calls, 4 failed
queries — all schema discovery by trial and error.

Added a `get_schema` tool: 3 turns, 0 failed queries.

The model had been improvising schema discovery by running `SELECT * FROM x LIMIT 1`
because it had no better option.

This is in `agent.py`.

**Generalizes to:** the tool description *is* the prompt. If the model doesn't have a
tool for something it needs, it doesn't stop — it improvises the most expensive
possible substitute and you pay for it.

---

## Aug 27 — Read tools and write tools need different levels of paranoia

Even when the sandbox code is identical.

Read-only stuff can only cause problems to my code tools. Write files can literally
tip over my computer, or delete or overwrite files on my hard drive. This is real
$hit right here.

> ⚠️ **Incomplete.** This is currently an assertion with no incident behind it.
> Needed: did the sandbox guard actually fire when pointed at `../.env`? What did the
> model do when it got the refusal back? Five lines turns this into the best security
> story in the phase.

---

## Undated — NameError: name 'X' is not defined

Can be 3 things:

1. You didn't import something
2. You didn't write a function for `X`
3. You wrote a function for `X` but it's **below** the code that's calling `X`

> Date unknown — reassign if you remember which day this was.

---

## ⚠️ MISSING from Phase 1

These happened, or were supposed to. None of them are written down:

- **Max-iteration guard tripping.** What made it trip, how many iterations, what the
  model was doing in the loop. Cheapest scar tissue in the phase and a good story.
- **Tool throws vs. tool returns an error string.** Two different designs, and the
  difference matters. What did the model do with each?
- **Sandbox guard firing on `../.env`.** See above.
- **The multi-step unattended run.** Messy quote emails → extract → pricing table →
  drafted response to disk. It worked. What was hard about getting it to work?
