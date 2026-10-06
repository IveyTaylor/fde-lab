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

**Another important takeaway:** you have to make sure the agent cant get out of the folder 
structure you want it in. Theres a function called WORKSPACE = Path("workspace").resolve()
This function basically makes sure that the agent CANNOT go outside of the path of your
current workspace. It cant go up a level and mess with your computer. 
**When you let an Agent write files on your file system, thats serious.

We did a test with a folder called /stolen and made sure that the LLM cant use the TOOL write_file
to write to a folder that you havent approved

**One more thing:** I tried to fool the Model into churning by putting a fake function about
diesel prices and asking a question about diesel prices. But the function only does RaiseError
So what dispatch() did was take the error message and go right to the part of else/if for an
error and reported that. It's interesting to note that the Model gave me its own version of 
text, not the text of the RaiseError

Another thing that came up was that the model confidently told me there were not customers
that didn't have any pickups...but there were 2 rows in the pickups table that HAD pickup_ids, but NULLS across pickup_date and outcome. 

My interview answer to "have you done this in an enterprise" is "no, but the failures I hit weren't in the model or the code, they were in the business term definitions, and-critically-the fix started with a conversation, not code."
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

## Sept 1
I wrote a couple of different ways for the system to return a list of customers who have had a pickup in the last 30 days. When I used the SYSTEM variable as the system prompt in response=client.messages.create, I got a better response, but it was really just lucky honestly. I never told the Model that it should check delivery_status=success...but it did when I used the system prompt. 

## Open for the rest of Phase 2

- [ ] Long-task amnesia run — watch the windowed agent forget the start of a task.
      **Log what it forgets first.**
- [ ] Compaction: summarize old turns, keep the summary. Note what the summary loses.
- [ ] Persistent memory: facts to SQLite between sessions, retrieve on start.
      What's worth persisting is a data-modeling problem.
- [ ] 200+ turn run. Find where it gets stupid.
- [ ] Post-mortem: *what broke and in what order*

Sept 3:
A good rule to remember that CAPITALS are constants like TOOLS = xxx
lower case could be a function or a construction that is created every turn or loop:
  while True:
      window = build_window(messages)

      params = {
          "model": MODEL,
          "system": SYSTEM if USE_SYSTEM else "",
          "tools": TOOLS,
          "messages": window,
      }

"params" is a construction that needs window to be built to function. 

## Sept 3
SYSTEM: you don't have to have a SYSTEM at all. Without it, the LLM acts generically.
SYSTEM is where you tell it "You are a dance instructor with an attitude". Also, system
is NOT part of messages, it's its own paramater, so it's ALWAYS there and always passed.

## Sept 4
A message is one top-level element of the list. Blocks inside it don't count.
So if you're doing a "window" to look at last N messages, you need to realize a message
is ALWAYS one from user, ALWAYS one from assistant (even if assisant does 3 tool calls:
that's three blocks, but only one message)

What we did today was work on the build_window function. Here's the code snippet:
MARKER = "Certificate of Destruction"

  PLANT = ("Rule for all quotes: hard drive destruction always includes a "
          f"{MARKER} line in the quote email.")
  PROBE = "Draft the quote email for a hard drive destruction job."
  messages = [{"role": "user", "content": PLANT}]
  plant_msg = messages[0]          # identity handle — see note 3

So the "plant" of "make sure blah blah certificate of destruction" in the tasks list.
Then we tried to get the Model to forget it, so we aged out the messages[0], but...BUT...it had an "echo", which was previous responses to destruction that said "blah blah certificate of Destruction"...so it kept doing the right thing as an "echo" of having been told the right thing before! (This is NOT a good way to code, by the way--we got a little bit lucky that the Model had this behaviour. If a real certificate is really required, I need to make sure that persists in messages somehow.)
the constraint survived eviction of its source message because copies of it persisted in the model's own prior outputs, and it failed on the first probe where no copy remained

The other takeaway from today is that meessages are differnt sizes. In one turn 6 messages was 2929 tokens, then later 6 messages wasa 5k tokens. So the real answer isn't to slice messages, its to go backward thru the messages until you get to the number you want to set as your limit.

Thanks tomorrow. :)

Claude's description of this:
"I built a message-count window and measured identical window lengths varying 69% in tokens within a single run, because tool results dominate payload. Count-based windows bound length, not cost — and cost is what you actually care about."

Finally got the error! I got to 50 messages, then task index 8, echo was true but we got an error where the first message was a tool result, but there wasnt a corresponding tool_use in teh message before it.

Observed one row where the marker was present in the window and the probe failed; no artifact captured because the run crashed before the dump. Unexplained.

I couldn't replicate that situation -- a passed = False while echo = True. It's a non-deterministic system, so anything can happen, but at least 80% of the time if echo (or plant) is True then passed is True.

The constraint outlives its own message

> *(Claude's draft — rewrite in my own words.)*

**What broke.** Nothing errored, which was the point. I planted a rule at
`messages[0]` ("hard drive destruction always includes a Certificate of
Destruction line"), ran 15 varied tasks through a 30-message sliding window,
and probed every few tasks to see whether the rule still held. The plant
evicted from the window at task 6. The probe kept passing through task 12 —
six tasks and 36 messages after the rule stopped being stated anywhere in
what I was sending.

**What I expected.** That behavior would break at, or shortly after, the turn
where the plant fell out of the window. It didn't.

**What actually happened.** Three separate findings.

*1. The echo carries the constraint.* Every probe that passed wrote the marker
back into history as part of the model's own output. Those assistant messages
sat in the window doing the work the plant used to do. Failure arrived when the
last copy left, not when the original did. Information doesn't leave context
when its message leaves — it leaves when the last copy leaves.

*2. The measurement propped up what it measured.* At a probe cadence of every
3 tasks, `echo_in_window` never went false: probes were regenerating the marker
faster than a 5-task window could drop it. I had to widen the cadence to every
8 tasks to observe failure at all. A probe that reinforces the thing it's
testing will report a constraint as durable indefinitely.

*3. `echo_in_window` has a false-positive mode.* One row read
`echo=True, passed=False`. Going into the dump, the marker was present — but
inside a message where the model was *declining* to draft the email and
offering options, one of which mentioned the Certificate line. The phrase was
there; the instruction was not. A boolean that greps for a string measures
string presence, not instruction presence, and those diverge whenever the model
talks about a rule instead of following it.

**Limitation, not controlled for.** The probe ("Draft the quote email for a
hard drive destruction job") supplies no customer, drive count, or date, so the
model sometimes asks for details instead of producing an artifact. An unknown
fraction of `passed=False` rows may be probe ambiguity rather than constraint
decay. Noted, not fixed.

**Reproduction note.** The first `echo=True/passed=False` row was lost — the run
crashed on a severed `tool_use`/`tool_result` pair before the dump wrote, and
three reruns didn't reproduce it. It reappeared only after the boundary guard
went in. Instrumentation that only runs on the happy path isn't
instrumentation; artifacts now write in a `finally` block.

**Numbers.** Window `keep=30`, no system prompt (`USE_SYSTEM=0`), probe every 8
tasks, 15 tasks. Plant evicted task 6 (`window_floor` 0 → 10 → 30 → 46).
Behavior held through task 12.

**Generalizes to:** you cannot tell whether a long-running agent is still
on-policy by checking whether it's currently complying. Compliance regenerates
its own evidence. The constraint that has held for a thousand turns because the
task kept invoking it will break silently the first time there's a lull.

Sept 5
Doing compaction today. 
Not JUST compaction, I took the function that compacts the data and put a standing 
rule in to check periodically to see if the plant_in_window (the plant for the rule,
which is to see if all emails about hard drive destruction have "destruction certification"
in there. The echo_in_function tracks if the Model has access to a message that
contains "destruction certificate", which is different from the rule itself.)

Lesson learned: put unbendable rules in the SYSTEM prompt, not in the conversation
  This is because unless you turn off SYSTEM, it gets sent in every single response call

Another lesson is that in the TOOLS block, your descriptions of the tools are the ONLY 
thing the model has to go on. If you say tool get_sql is good for internet recipes, it's 
going to use that if the question is about internet recipes. Putting a bad description is
a real **BUG**

I've been wrestling for a few hours with the ability to test whether or not an email has been sent. The compaction didn't tell me for sure whether the email ACTUALLY went out, it just tested for some text indicating an email was being drafted. Sometimes the Model would say "I will draft an email with these words", but not actually do the TOOL call to create a file. We ended up with tracking that it drafted the actual email, but in some cases it never called the TOOL to create the file. So my decision here is to not "fix" that, because the purpose here is to make sure compaction doesn't lose the email. If this was a Prod AI pipeline that was creating actual email files to go to actual clients, we'd have to fix that, but this is a learning exercise.

# Phase 2 Post-Mortem — Context & Memory

## What got built
- Token accounting via count_tokens, gating compaction
- Sliding window (build_window/safe_boundary) — built, deliberately disabled to isolate compaction's effect
- Compaction (compact()) — LLM-summarizes old turns, keeps recent N verbatim
- Third tool: get_weather (Open-Meteo, geocode + forecast) — real HTTP call, distinct from the
  deliberately-broken get_price_of_fuel stub
- The "amnesia run" harness: plant a standing rule, run tasks, probe periodically, measure survival

## Bugs found, in order (this is the meat — what broke, what you tried, what fixed it)
1. Tool input key mismatch: dispatch() read tool_input["city_name"], schema declared "city" — 
   [why this class of bug happens: model fills the schema you wrote, not the name you meant]
2. plant_in_window used object identity (`is plant_msg`), not content — always False after any
   compaction regardless of whether the rule actually survived. Fixed to substring-check PLANT
   itself, distinct from echo_in_window's looser MARKER check.
3. Probe cadence (`i % 8 == 0`) was decoupled from when compaction actually happened — could
   record "plant survived" readings that were really just "compaction hadn't fired yet."
   Fixed: probe fires immediately after a compaction event, not on a fixed schedule.
4. Duplicate record logging — run_probe() already appended/printed; call sites repeated it.
   [note: classic refactor trap — function already has the side effect, don't repeat it outside]
5. Real classifier bug: passed/outcome only checked the model's closing remark (`final`), not
   tool_use inputs — so a genuine compliant draft written via write_file was misclassified as
   no_draft, because the marker text lived in the tool call, not the spoken reply.
   Fixed by accumulating all text + tool_use inputs per turn (`full_activity`) and classifying
   against that.
6. Summary text was unrecoverable after the fact — compaction folds each prior summary into the
   next one, and dump_messages() only captures final state. Fixed by logging summary_text and
   probe_activity into each record at the moment they're produced.

## The finding — compaction summarizer role confusion
- compact() calls the model with no `tools`, no `system` — reproduced TWICE independently:
  - re: database access ("I don't have access to actual data from your system...")
  - re: weather ("I don't have access to real-time weather data or the ability to browse
    the internet...")
- Two reproductions in unrelated domains = a structural property of the design, not a fluke:
  the summarizer, missing agent context, sometimes answers as itself instead of reporting
  what the transcript showed.
In both reproductions, the hallucination never reached the user — the agent second-guessed its own false claim and used its tools anyway. Measured cost was small: one redundant database query in the first case, effectively nothing in the second, since the weather call would've been necessary regardless. But the fact that it turned out fine twice is not evidence the design is safe — it's evidence the model happened to override its own bad information both times. Nothing here stops it from trusting the false claim instead, especially where re-verifying is expensive or the underlying fact truly cannot be re-derived by the agent alone.

## The finding that didn't hold up — and why that's still worth writing down
- Hypothesis: a compaction summary that frames the task as blocked/incomplete keeps causing
  no_draft outcomes on future probes.
- Evidence against: a window with a hallucinating, wrong summary still produced two clean
  passes right after it — the model overrode the false claim and used its real tools anyway.
- [Write: what's the actual variable, then? You didn't fully pin this down — say so plainly.
  Half-finished analysis stated honestly is worth more than a tidy wrong conclusion.]

## Design decision made on purpose (not a bug)
- classify_probe's "passed" doesn't require an actual file write — content compliance anywhere
  in the turn counts, whether via write_file or inline text.
- Reasoning: this test measures rule survival, not deliverable completeness.
- Contrast: a client-facing pipeline would require the file, since a downstream agent/human
  needs a real artifact to act on — not a paragraph in a chat log.
We ended up with tracking that it drafted the actual email, but in some cases it never called the TOOL to create the file. So my decision here is to not "fix" that, because the purpose here is to make sure compaction doesn't lose the email. If this was a Prod AI pipeline that was creating actual email files to go to actual clients, we'd have to fix that, but this is a learning exercise.

## Also worth a line
- Agent self-recovered from a real UnicodeEncodeError (charmap can't encode '\u2713') on a
  write_file call — diagnosed the cause, rewrote with ASCII bullets, succeeded on retry,
  unprompted. [Unrelated to compaction — just good evidence of resilience.]

## Still open — not done yet
- Scale the amnesia run to the real 200-turn target (been debugging on short slices)
- Persistent memory to SQLite across separate script runs — not started at all
- Decide: should classify_probe distinguish "drafted+saved" from "drafted, not saved" as
  separate outcomes for a production-oriented version? (Deferred on purpose — say why.)
- Phase 1 post-mortem — confirm whether this ever actually got written

## Lesson UnboundLocalError 
When Python looks at a function definition, it looks at every variable in there as local for the whole function including all iterations of loops. So you can use the value of a variable in a function, but when you CHANGE the value, it needs to have that variable defined inside the function. 
So the pattern, worded more precisely:

Create the variable once, at module level, with a normal assignment: turn_count = 0.
Inside any function that needs to modify it, add global turn_count — not to give it a value, just to tell Python "don't shadow this name locally."
Then assign to it normally, same as you would anywhere else: turn_count += 1.
(Claude's take on the same thing as above)
One more thing worth knowing so you don't over-apply this: you only need step 2 if the function is going to assign to the name. If a function only ever reads turn_count — say, printing it, or checking if turn_count >= 200 — no global is needed at all, because reading never triggers Python's "this name is local" rule. That rule only fires on assignment. So global is specifically for "I'm about to change the one that lives outside," not a blanket requirement for touching a module-level variable at all.

The "gotcha" here is if you get this wrong, but you don't modify the value, you won't ever know. If the function just calls the variable, you don't get an error, it just returns the value of the global namespace's variable. Which is a problem if you wanted the function to have its own value. The error only raises itself if you try to CHANGE the value without declaring it in the function namespace. Good news is the error would be pretty good: "UnboundLocalError: local variable 'turn_count' referenced before assignment"

"globa namespace" = "module namespace" = "module scope"
In a function that's "local namespace"
Python's official name for the whole lookup order is LEGB — Local, Enclosing, Global, Built-in. When a function reads a name, it checks its own local namespace first, then any enclosing function's namespace (relevant for nested functions, which is what nonlocal targets), then the module's global namespace, and finally the built-ins (where len, print, range, and so on live)

## I asked Claude what's up with this statement
records.append(record)
print(f"probe @ task {task_index:>4}: outcome={record['outcome']:<8} "
          f"plant={str(record['plant_in_window']):<5} echo={str(record['echo_in_window']):<5} "
          f"tokens={record['input_tokens']}")
    return record

1. 3 lines of print(f"") get glued together automatically by Python. It's for readability.
2. record is a DICT, not a LIST. Note that records (with an s) IS a list.
Since record is a dict, record['outcome'] maans give me the value of outcome for this dict
This is the same as when I grabbed records from a table using SQLite:
  run_sql(): conn.row_factory = sqlite3.Row followed by [dict(r) for r in rows]
This gives me a LIST of DICTS. This allows me to call row['customer name'] instead of having to remember customer name is the 3rd column in the row.
3. The stuff like {task_index:>4}. Stuff to the left of the colon is what I want displayed, and to the right is formatting. What I'm doing here is asking for teh task_index, but I want it 4 characters wide right aligned. So 1 becomes "   1", 302 becomes " 302". This is just for readability.
{record['outcome':<8]} means I want the first 8 characters of outcome left aligned with spaces at the end. This way it prints "plant=passed" or whatever.

break ONLY has meaning inside a for or while loop

Post Mortem:
Plant survival is one-way. Once it's gone to compaction, it's gone forever. That makes sense, becuase it's a rule specified at the start looking for an exact string. The LLM eventually paraphrases the phrase and then it's gone. But, BUT echo comes and goes. I think this is because it's just a good idea in general to have a "certificate of destruction" for a hard drive.

There was only one failure to have the word "certificate", and that had the word "certification", so that was a very edge case, but when I was only looking at 20 turns, I thought it was much more common. It was only wnen I did 200 turns and it never reappeared that I realized how rare that was.

No_draft streaks--there were 2 long no_draft streaks, and these were mostly the model asking for more information. If I was to redo this, I would ask a much more specific question, something with no ambiguity whatsoever. The Probe question, if it was better, the outcome would be better.

I have to set my laptop to not go to sleep when running long stuff. In the 200 turn test, I went to the gym and thought it took over an hour to complete (and I blamed my wimpy laptop). Claude told me that ALL the latency is on the API replying, Python code is fast as hell, and I just need to make sure my laptop doesn't go to sleep. I reran and it completed in 10 minutes.

Quiz Thoughts: (I asked C to give me a 10 question quiz on what I should know right now)
Demo (20 turns) isn't as good as 200 (production) because a demo is small BY DESIGN. It's not going to run the full gamut of functionality like compaction. The things that change your agent's behavior (long message lists, compaction, etc) never happen in a demo of 20 turns. This is why you code with 20 and test with 20 and then 200.
Why use smarter slower models? Because when you're running an experiment to see whether compaction causes things to fail, you don't want ANY other noise in the system. For this, you want the best, smartest model you can get. You want to be as sure as possible it isn't the model. This is simply controlling an input to an experiment--smarter model has less noise.
After all the Probe stuff and is "certificate of destruction" there or is the echo there...the SYSTEM is never compacted, so put any rules like that (for now) in SYSTEM. There's a better way I'll learn later (SQLite persistence is a good answer, but also a second agent test this one), but this is the best answer right now.
What does the Model use to choose TOOL? Your Description and the input_schema. That's it. Write the description as well as you possibly can.
What's REALLY lost in compaction? DETAILS!!!! You keep the "gist", but lose the details. The compaction of several "gists" loses even more details (by design). If that's not good enough, do something else. 
What do you lose with a Window? EVERYTHING not in the window! No "gist", no nothing...it never happened. But it IS cheap, and no chance of losing details and hallucinating that way.

## Persistence
One thing to point out is that you DONT want to call get_sql, the function the Model can use, to do this. You don't want ANY choices here, you want this to load by itself every single time. The TOOLS block is for the Model--this is code you are writing to force policy info to be in the SYSTEM, every turn, every message, every time.

  ## Cool trick to bypass everything and just run some python (to clarify JUST what youre trying to troubleshoot) (do this in bash)
  python
  >>> import sqlite3
  >>> conn = sqlite3.connect("shane.db")
  >>> conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

  ## Where does models "decision" code live vs my deterministic stuff?
  Anything the Model is going to choose starts with TOOLS and goes thru dispatch()
  Anything I want to happen deterministically (like adding policies to system) does not go thru dispatch(). It just happens based on whatever criteria I decide.

What I built: Two-part SQLite persistence — a policy table loaded unconditionally into system at startup (not a tool call, since it has to run every session regardless of model judgment), and a remember tool gated on an explicit user request, writing to a memory table via one fixed parameterized INSERT.

What broke #1 — DB Browser silently didn't save. Built the policy table and stub rows in DB Browser for SQLite, queried it there, worked fine. Ran the actual script — sqlite3.OperationalError: no such table: policy. DB Browser doesn't autocommit; my changes were sitting in an open transaction the GUI could see but the file on disk couldn't. Tell: a leftover shane.db-journal file that should've been cleaned up on commit and wasn't. Diagnosed by bypassing DB Browser entirely — opened a fresh Python sqlite3 connection and queried sqlite_master directly, the same mechanism my real code uses. Fixed with File → Write Changes. Lesson: a tool's own UI is not ground truth for what's persisted; check the file directly, with the same code path that's actually failing.

What I verified: remember fires on an explicit ask (confirmed a real row landed). Then tried to break the gating on purpose — fed it a real, useful fact phrased as an ordinary question, no "remember" framing. No row written. The tempting case held.
