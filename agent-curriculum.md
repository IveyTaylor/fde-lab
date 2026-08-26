# Agent-Building Curriculum

**Version 2 · Rebuilt August 26, 2026** (v1 written Aug 20, lost)
**Owner:** Fort Mill, SC → Forward Deployed Engineer
**Capacity:** ~15 hrs/week. Daily granularity is scaffolding; the weekly gate is the rule.

Upload this to the Claude Project next to `Career-Coach-Context.md` so it loads at the start of every session.

---

## Ground rules

1. **Hand-rolled before frameworks.** Every abstraction gets built by hand once before you're allowed to use the library version. The point is to know what the framework is hiding, because that's what gets asked in interviews and that's what breaks in production.
2. **No coding agents during the learning phase.** If you didn't type it, you didn't learn it. Reading generated code feels like understanding and isn't. This rule relaxes after Phase 5.
3. **No separate Python course.** You already read and modify Python at a working level; that's most of the distance. A course would take four weeks, feel like progress, and leave you having still never called an LLM API. For someone whose failure mode is procrastination that looks like preparation, a prerequisite course is the perfect trap — it's legitimate, it's productive, and it's not the work.
4. **Build it, then break it.** Every phase includes deliberately breaking the thing you just built. The scar tissue is the deliverable; the working code is a byproduct.
5. **Fixed time block, same hours daily.** Pick it and put it on a calendar. Given the oversleeping, don't pick 6am and then fail at it — pick something you'll actually hit, even if it's 10am–1pm.
6. **Every phase ends with a written post-mortem** in `/notes` — what broke, what you tried, what fixed it. 300 words, ugly is fine. These notes are the raw material for interview answers. They're not optional; they're half the point.
7. **Everything is committed and pushed to a public repo.** Weak accountability, but non-zero, and it becomes the portfolio artifact.

---

## Deadline structure

Internal deadlines won't hold. Structure:

- **Weekly gate.** The week's deliverable is committed and pushed, and the post-mortem is written. You report: what shipped, what didn't, what you're carrying into next week.
  - *Amended Aug 19:* the gate check is **Sunday night**, not Friday, because weekend work is a real part of your schedule. Build to Thursday anyway. Sunday is the valve, not the plan.
- **Within a week, shuffle freely.** Front-load, back-load, six hours on a Saturday. What's fixed is the 15-hour weekly total and the gate.
- **External forcing function.** The friend-business process-mapping conversations get scheduled for real calendar dates. Once someone else is expecting you on a date, the deadline stops being fictional. This is the main reason to start those conversations before you can build anything.

---

## Phase 0 — Raw API fluency ✅ COMPLETE
**Week 1 · Aug 17–21 · Gate: Aug 21**

| Day | Work |
|---|---|
| Mon 8/17 | Repo, venv, API key, credits. One call to the Messages API. Print the **raw JSON response** — not the convenience accessor. Read every field. Commit. |
| Tue 8/18 | Multi-turn. Build the messages array by hand. CLI chat loop that maintains history. System prompt. `max_tokens`, `temperature` — change them, observe. |
| Wed 8/19 | Tokens and money. Log `usage` on every call. Compute running cost. Then **deliberately overflow the context window**. Read the error. Write down exactly what happens. |
| Thu 8/20 | Structured output. Get reliable JSON back. Parse it. Now make it fail — and handle the failure. Retry logic. |
| Fri 8/21 | Streaming. Error handling for rate limits and overloads. README. Post-mortem. Push. |

**Deliverable:** a working multi-turn CLI chat client, with cost logging, written from an empty file.

**Headline finding (keep this — it's the most interview-usable thing produced so far):** output quality collapsed at roughly **15% of the context window**, starting at turn 3 and total by turn 11, with `stop_reason: end_turn` and no error the entire time. Token growth ~2,810/turn. A long-running agent doesn't announce that it's broken — it gets quieter, vaguer, and more repetitive while every metric stays green.

**Open threads carried forward:** README at repo root (deferred repeatedly). Varied-input degradation test — does a genuinely varied conversation collapse the same way, or does that failure mode require degenerate input?

---

## Phase 1 — The agent loop, by hand 🔄 IN PROGRESS
**Week 2 · Aug 24–28 · Gate: Sunday Aug 30 (build to Thursday — Friday is golf)**

The single most important week in this plan.

- Tool definitions: JSON schema, descriptions, why the description is the actual prompt.
- Parse `tool_use` blocks out of the response.
- Execute the tool. Return `tool_result`. Loop until the model stops asking.
- Multi-step: force a task that requires 3+ tool calls in sequence.
- Failure handling: tool throws, tool returns garbage, model calls a tool that doesn't exist, model loops forever. Build a max-iteration guard and watch it trip.

**Deliverable:** an agent with 3+ real tools (file read/write, HTTP fetch, and a SQL query tool against a local SQLite DB — play to your strength) that completes a multi-step task unattended.

**Status as of Aug 26:**
- ✅ Tool loop working — `b77bbf3`, SQL agent with a schema tool
- ✅ Tool description tuning measured (six turns → three)
- ❌ Third and fourth tools — file I/O and HTTP fetch. Both current tools hit SQLite; the model never has to choose *which* tool, only *whether*.
- ❌ Multi-step unattended task. Suggested: read a file of messy quote emails → extract structured fields (reuse `extract.py`) → query a pricing table → write a drafted response to disk. That's the October Shane build in miniature, on fake data.
- ❌ Failure handling and max-iteration guard
- ❌ Post-mortem

**Also this week, outside the 3 hours:** contact **2** friend-business owners and put a process-mapping conversation on the calendar for the first half of September. Use the script in the context file. Do not promise a build. *(Shane Hunt / Records Reduction is in motion. Owner #2 is unidentified — this is the gap.)*

---

## Phase 2 — Context and memory
**Week 3 · Aug 31 – Sep 4 · Gate: Sun Sep 6**

Your named blind spot, and the thing that generated the interview question you couldn't answer. Treat this week as deliberate damage.

- Token accounting: count before you send, not after you fail.
- Sliding window. Watch the agent forget the beginning of the task. Note what breaks first.
- Compaction: summarize old turns, keep the summary in context. Watch what the summary loses.
- Persistent memory: write facts to SQLite between sessions, retrieve on start. Decide what's worth persisting — this is a data-modeling problem and you're good at those.
- Long-run degradation: run the Phase 1 agent for 200+ turns. Log everything. Find where it gets stupid.

**Deliverable:** the Phase 1 agent survives a 200-turn session without falling over, plus a post-mortem specifically titled *what broke and in what order*.

**Interview value:** this week converts "no idea" into "here's the failure mode, here's what I tried, here's the tradeoff." That's the difference between a pass and a screen-out.

---

## Phase 3 — RAG, in code, on messy data
**Week 4 · Sep 7–11 · Gate: Sun Sep 13**
*(Labor Day Mon 9/7 — either work it or accept a 4-day week and say so up front.)*

You've done RAG once, platform-abstracted. That taught you the shape, not the mechanics.

- Embeddings: what they are, generating them, storing them.
- Chunking: fixed, recursive, semantic. Chunk boundaries destroying meaning.
- Vector store: start with a local one. Metadata filtering.
- Hybrid retrieval: vector + keyword. Why pure vector fails on identifiers, part numbers, names.
- **Retrieval evaluation.** Build a small labeled question set and measure whether you're actually retrieving the right chunks. Most people skip this. You have a data-quality background — don't.

**Deliverable:** RAG over a genuinely messy corpus (not clean markdown — PDFs, inconsistent formatting, tables) *with* a retrieval eval harness that produces a number.

---

## Phase 4 — MCP and what frameworks hide
**Week 5 · Sep 14–18 · Gate: Sun Sep 20**

Now that you've built it by hand, look at the abstractions.

- MCP: the protocol, servers vs. clients, transports. **Build an MCP server** exposing something real — start with your Phase 1 SQL tool.
- Connect it to Claude Desktop or Claude Code and use it as an actual user.
- Then pick *one* framework and rebuild your Phase 1 agent in it. Write down what it saved and what it hid.

**Deliverable:** a working MCP server, plus a side-by-side comparison note.

**Market note:** MCP is the thing consultancies are currently hiring for by name. This week has the highest résumé-keyword return of any week in the plan. It is also the week where your Phase 1–3 work pays off, because you'll understand what the server is actually doing.

---

## Phase 5 — Evaluation and reliability
**Week 6 · Sep 21–25 · Gate: Sun Sep 27**

The week that separates you from every bootcamp graduate, and the one that maps most directly onto what you already know.

- How do you know an agent works? Test cases, golden outputs, LLM-as-judge and its failure modes.
- Regression testing when you change a prompt.
- Observability: tracing, logging every call, latency and cost per run.
- Guardrails: input validation, output validation, refusal handling, cost ceilings.
- Determinism where you can get it, and being honest about where you can't.

**Deliverable:** an eval suite over the Phase 1–3 agent that you can run and that produces a pass/fail report.

**Why this is your edge:** you spent years on data quality and observability. Almost nobody entering this field can answer "how would you know if this agent regressed in production." You can, and it's the same discipline you already have. Say so in interviews.

---

## Phase 6 — Capstone: the friend-business build
**Sep 28 – Oct 30 · Gate: demo on Oct 30**

- **Week of 9/28:** process map the chosen workflow. Do this the way you already do it professionally. Write it up properly — the artifact matters as much as the code.
- **Weeks of 10/5 and 10/12:** build.
- **Week of 10/19:** put it in front of the real user. Watch them use it. Do not explain it to them first.
- **Week of 10/26:** fix what they hated. Demo. Write the case study.

**Scope rule:** one high-frequency, low-stakes process. Intake triage, quote generation from a template, weekly report assembly. If you can't describe it in one sentence, it's too big.

**Output:** a demoable thing, a written case study, and the sentence *"I automated intake and quoting for a construction company"* — which is what actually answers "have you done this in an enterprise before."

---

## Checkpoints

| Date | Checkpoint |
|---|---|
| ~~Fri Aug 21~~ | ~~Phase 0 gate.~~ ✅ Cleared |
| **Sun Aug 30** | **Phase 1 gate + friend-business conversations on the calendar.** |
| Sun Sep 6 | Phase 2 gate. |
| Sun Sep 13 | Phase 3 gate. |
| Sun Sep 20 | Phase 4 gate. |
| Sun Sep 27 | Phase 5 gate. **Résumé rewrite starts — there's now something to put on it.** |
| Late Sep | Interview prep begins per context file. |
| Fri Oct 30 | Capstone demo. |

---

## What "slipping" looks like

Not a missed day. A missed day is normal. These are the signals:

- Two consecutive weekly gates with no commits.
- A week spent "researching" or "getting set up" with nothing pushed.
- Reaching for a framework before Week 5 because the by-hand version is frustrating. **The frustration is the curriculum.**
- Rewriting this plan instead of executing it. One revision at the Phase 2 gate is allowed. More than that is procrastination in a plausible costume.
