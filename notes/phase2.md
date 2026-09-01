# Phase 2 — Context and memory

**Week 3 · Aug 31 – Sep 4, 2026 · Gate Sun Sep 6 · IN PROGRESS**
Deliverable: the Phase 1 agent survives a 200-turn session without falling over, plus
a post-mortem titled *what broke and in what order*.

---

## Aug 31 — Token accounting: what count_tokens actually tells you

If you look at `client.messages.count_tokens()` right before the Model call:

It always gives you the **input** tokens. Why? B/c we don't KNOW the output tokens
yet — the Model decides what to reply with and then you programmatically add those to
the messages, so they show up in the next input_tokens count.

The count_tokens is driven by the TOOLS stuff (in my case like 900 tokens), and then
when I made `get_schema` that was another 400 tokens (it asks for DDL of every single
table... which is okay with my 3 tables but if it's a huge database that's a huge
problem).

The "hard work" was really under 200 tokens — to write the email and to build the
file and to reply to me. That was done by my local computer, not the Model.

**There isn't a premium for "hard work" by the Model. You pay for the size of the
response.** Now, HAD I ASKED for a long email, that's a lot more output tokens.

The other really important thing here is that when TOOLS cost me 900 for the first
turn, it cost me that same 900 for EVERY TURN. Same thing with the get_schema dumping
all the DDL.

**Big takeaway:** you can call some serious token-eating monsters up at the start of a
session, like I did.

- Make sure when you go to prod that you are **CHOOSING** tools, not sending all of
  them in.
- Make sure when you go to prod you debug any sort of `get_schema` to make sure it's
  not thousands or millions of characters.

One last thought about cost — the Model is trying to limit cost. When I asked it to
create an email for "a customer", it sent a query with `LIMIT 1` at the end. Nothing
to do with my code, just the model being smart and generally on the side of parsimony.

---

## Aug 31 — A/B cost comparison: one customer vs. all customers

> 🔴 **THIS SECTION IS CLAUDE'S PROSE, NOT MINE.** The table is my measurement; the
> analysis under it is not. Rewrite the takeaways in my own words and delete this
> banner. Per ground rule 2 — if I didn't type it, I didn't learn it.

| Turn | A: one customer | B: all customers | Δ A | Δ B | What happened |
|---|---|---|---|---|---|
| 1 | 990 | 982 | — | — | ~950 of TOOLS, riding along free of charge |
| 2 | 1,430 | 1,416 | +440 | +434 | get_schema moves in permanently |
| 3 | 1,634 | 1,878 | +204 | +462 | A: one row. B: eight rows, three columns |
| 4 | 1,832 | — | +198 | — | A still had a file to write |
| **Input** | **5,886** | **4,276** | | | |
| **Output** | **503** | **498** | | | |
| **Cost** | **$0.0084** | **$0.0068** | | | |

*(Claude's analysis — to be rewritten:)* Eight rows cost 2.3× what one row cost, +462
versus +204, on a trivially small result set. Scale it to 800 rows and turn 3 alone
adds ~46,000 tokens that ride along on every subsequent turn forever. Run B was
cheaper overall despite the fatter payload, because it finished in three turns instead
of four — no `write_file` call. Turn count and payload size are separate cost drivers
and they don't move together. The model chose `LIMIT 1` in A and no limit in B, purely
off the singular/plural in the question. It was right both times. It won't always be.

**Three findings, condensed:**

1. Fixed tool overhead is ~950 tokens/turn, 96% of turn 1, paid forever.
2. Tool result size compounds — cost is payload × remaining turns, not payload.
3. Fewer turns can beat smaller payloads. Optimize for round trips first.

---

## Aug 31 — tool_use blocks and tool_result must stay paired

You have to have the `tool_use` block with the ID in order for the Model to use the
output of a tool. Without that context, the Model determines whatever it is (SQL from
`run_sql`, DDL from `get_schema`) is just nonsense. It's stateless so it has no idea
what you're sending it, so it kicks an error for you sending it nonsense.

> Date uncertain — this may belong in Phase 1. But it's the constraint that produced
> the 400 when the sliding window sheared a pair, so I've filed it here.

**Still to write:** the actual sliding-window 400. What the window dropped, what the
error said, and the rule I ended up implementing to keep pairs intact.

---

## Open for the rest of Phase 2

- [ ] Long-task amnesia run — watch the windowed agent forget the start of a task.
      **Log what it forgets first.**
- [ ] Compaction: summarize old turns, keep the summary. Note what the summary loses.
- [ ] Persistent memory: facts to SQLite between sessions, retrieve on start.
      What's worth persisting is a data-modeling problem.
- [ ] 200+ turn run. Find where it gets stupid.
- [ ] Post-mortem: *what broke and in what order*
