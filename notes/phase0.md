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
