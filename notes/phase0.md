# Phase 0 — Raw API fluency

**Week 1 · Aug 17–21, 2026 · Gate cleared Aug 21**
Deliverable: multi-turn CLI chat client with cost logging, written from an empty file.

---

## ⚠️ MISSING — the headline finding (write this first)

This is the single most portfolio-relevant thing produced in Phase 0 and it does not
exist in written form anywhere. The instruction to write it survived; the note did not.

Data points I have from the run:

- Token growth ~2,810 per turn
- Output quality began degrading at turn 3
- Total collapse by turn 11
- Collapse happened at roughly **15% of the context window** — nowhere near the limit
- `stop_reason: end_turn` the entire time. No error, no warning, every metric green
- Rate limit ambush (details needed — what hit, when, what the error said)

**Write it in my own words, four beats:**
1. What broke — the specific symptom
2. What I thought was wrong — including the wrong guesses
3. What actually fixed it / what it turned out to be
4. What it generalizes to — the sentence I'd say to a stranger

Paste the raw output underneath. Then commit.

---

## Aug 20 (date inferred) — Structured output: nullable fields hide failure

A validation rule that permits null gives the model a legitimate way to satisfy the
check without solving the problem. Sometimes that's correct — as it was here.
Sometimes it's a silent failure, if you actually needed a value.

Whether nullable is right is a **business decision, not a technical one.** That's a
question for the process owner (Shane), not something to settle in the schema.

---

## Open threads carried out of Phase 0

- Repo-root README — deferred repeatedly, still open
- Varied-input degradation test: does a genuinely varied conversation collapse the
  same way, or does that failure mode require degenerate input?


Output quality collapsed at roughly 15% of the context window. Degradation started at turn 3, total by turn 11. Token growth ~2,810 per turn. stop_reason: end_turn the entire time — no error, no warning, every metric green the whole way down. The framing you landed on: a long-running agent doesn't announce that it's broken. It gets quieter, vaguer, and more repetitive while everything you're monitoring says it's fine.

I don't remember the exact input or output, but it was basically sending back smaller and smaller text blocks answering the question more and more wrong. Moral of the story, if the agent is turning and turning but providing worse results, something is wrong--most likely its using a tool the wrong way.

five lines: the token growth rate (~2,810/turn), the output collapse with the numbers, the fact that it never errored, and the rate limit ambush. Paste the raw output underneath. Commit it.

This is the most portfolio-relevant thing you've produced in two days. Don't lose it.

Worth adding to your notes, because it's a subtle finding: a validation rule that permits null gives the model a legitimate way to satisfy the check without solving the problem. Sometimes correct — as here. Sometimes it's a silent failure, if you actually needed a value. Whether nullable is right is a business decision, not a technical one, and you'd ask Shane.

Here's a good note: when you use a sql query function as a tool, you can waste a lot of money pulling "select * from tblA" just to get the metadata of a table.
I used up six turns by asking it to pull data from 3 tables without any schema help:
    ------------------------------------------------------------------------------------------------------------
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
    ------------------------------------------------------------------------------------------------------------
Now I'm going to do a schema deal-e-o and see if that minimizes my number of turns and/or how much data it calls
...I missed out on what teh result of that actually was...sorry bruh.

Aug 25, 2026
Agent with three table names in the tool description: 6 turns, 5 API calls, 4 failed queries — all schema discovery by trial and error. Added a get_schema tool: 3 turns, 0 failed queries. The model had been improvising schema discovery by running SELECT * FROM x LIMIT 1 because it had no better option.
This is in agent.py

read tools and write tools need different levels of paranoia even when the sandbox code is identical. Read only stuff can only cause problems to my code tools.....write files can literally tip over my computer, or delete or overwrite files on my hard drive. This is real $hit right here.

8/31 Some things I learned today:
If you look at client.messages.count_tokens() right before the Model call:
    It always gives you the input tokens. Why? B/c we don't KNOW the output tokens yet, the Model decides what to reply with and then you programmatically add those to the messages, so they show up in the next input_tokens.count. 
    The count_tokens is driven by the TOOLS stuff (in my case like 900 tokens), and then when I made get_schema that was another 400 tokens (it asks for DDL of every single table...which is okay with my 3 tables but if it's a huge database thats a huge problem). 
    The "hard work" was really under 200 tokens, to write the email and to build the file and to reply to me. That was done by my local computer, not the Model.
    There isn't a premium for "hard work" by the Model. You pay for the size of the response.
        Now, HAD I ASKED for a long email, that's a lot more output tokens!!!!
    
    The other really important thing here is that when TOOLS cost me 900 for the first turn, it cost me that same 900 for EVERY TURN!!!! Same thing with the get_schema dumping all the DDL.

    So the big takeaway here is that you can call some serious token-eating monsters up at the start of a session, like I did.
        Make sure when you go to prod that you are CHOOSING tools, not sending all of them in.
        Make sure when you go to prod you debug any sort of get_schema to make sure it's not thousands or millions of characters.

    One last thought about cost...the Model is trying to limit cost. When I asked it to create an email for "a customer", it sent a query with LIMIT 1 at the end. Nothing to do with my code, just the model being smart and generally on the side of parsimony.

This is me and Claude looking at 
    Turn    A: one customer B: all customers    Δ A Δ B What happened
1           990             982 —   —   ~950 of TOOLS, riding along free of charge
2           1,430           1,416   +440    +434    get_schema moves in permanently
3           1,634           1,878   +204    +462    A: one row. B: eight rows, three columns
4           1,832           —   +198    —   A still had a file to write
Input       5,886           4,276           
Output      503             498         
Cost        $0.0084         $0.0068         

The headline: eight rows cost 2.3× what one row cost. +462 versus +204, and that's a trivially small result set. Scale it — 800 rows instead of 8 — and turn 3 alone adds ~46,000 tokens that then ride along on every subsequent turn forever. Your get_schema finding, an order of magnitude worse.

The unexpected part: run B was cheaper overall. It finished in three turns instead of four, because listing customers doesn't require a write_file call. One fewer round trip beat one fatter tool result. That's the tradeoff you sketched Thursday for the 20-user question, now with numbers on it: turn count and payload size are separate cost drivers, and they don't move together.

Model chose LIMIT 1 in A and no limit in B. Nothing in your code changed. It read the singular/plural in your question and made a cost decision on your behalf, unprompted and unenforced. It happened to be right both times. It won't always be.

Three findings for the post-mortem, and they're clean:

Fixed tool overhead is ~950 tokens/turn, 96% of turn 1, paid forever.
Tool result size compounds — cost is payload × remaining turns, not payload.
Fewer turns can beat smaller payloads. Optimize for round trips first.

NameError: name 'X' is not defined. Can be 3 things:
    1. you didn't import something
    2. you didn't write a function for 'X'
    3. you wrote a function for 'X' but its BELOW the code thats calling X

You have to have the tool_use block with the ID in order for the Model to use the output of a tool. Without that context, the Model determines whatever it is (sql from run_sql, DDL from get_schema) is just nonsense. It's stateless so it has no idea what you're sending it, so it kicks an error for you sending it nonsense.


