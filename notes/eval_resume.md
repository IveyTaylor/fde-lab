# Resume here: eval.py (Phase 3 retrieval eval)

*Saved Oct 7, 2026 before dinner. Gate: **Sun Oct 18** (recall@5 for fixed vs. structure). Capstone demo: Fri Oct 30.*

## Where we are

- `rag/search.py` **works**: `load_index()` (with model/count/dim checks) and `search(question, records, k=5)` returning `(score, record)` pairs, best first.
- Hand-tested 3 eval questions:
  - **q04** wind shear: expected page (Aviation Weather p.8) ranked **#1** (0.735).
  - **q01** altimeter interval: unanswerable; top score was **0.818**, *higher* than a real hit. Cosine measures topic, not "contains the answer."
  - **q02** AC 43-203B: returned the CANCELLATION chunk ("203A is canceled"), wrong chunk on the right page. Identifier weakness; will score as a page-level HIT anyway.
- `rag/eval.py` **started**: imports, `BASE_DIR`, `QUESTIONS_PATH` are correct. `load_questions` is not working yet.

## Fix list for the current `load_questions`

1. `json.loads(...whole file...)` will fail with "Extra data: line 2". The file is **20 JSON objects, one per line**. Read the text, `.splitlines()`, skip blank lines, `json.loads` **each line**.
2. Use the `path` **parameter** inside the function, not `QUESTIONS_PATH`. The caller decides which file.
3. Append the **whole dict** (`i`), not `i["question"]`. You need `expected`, `type` and `id` later.
4. Delete `test = load_index`. It's after `return` (never runs) and has no parentheses (stores the function, doesn't call it).
5. `return questions`, no parentheses needed.
6. In `__main__`: delete the stale `start_page/end_page` comment, then:
   ```python
   questions = load_questions(QUESTIONS_PATH)
   print(len(questions))           # expect 20
   print(questions[1]["expected"]) # q02's answer key
   ```

**Done when:** it prints `20` and q02's expected list.

## Then, in order

- [ ] **`is_hit(results, expected)`**: nested loops. Outer: each `(score, r)` in results. Inner: each `e` in expected. Hit if `r["source_file"] == e["source_file"]` **and** `r["page_start"] in e["pages"]` → `return True` right away. Where does `return False` go? (After **both** loops, not inside. Same family of bug as the `return`-inside-the-loop in `search()`.)
- [ ] **`run_eval(index_path, questions, k=5)`**: load the index **once**; set `hits = 0`, `scored = 0`; for each question, `continue` if `type == "unanswerable"`; search, check `is_hit`, count, and print one line: `id | type | HIT/miss | top result file p.page`. End with `recall@5 = hits/scored`.
- [ ] Run it on **`embeddings.json`** (fixed) and **`embeddings_structure.json`** (structure). Two numbers = the gate.
- [ ] Write the results into `notes/Phase3.md`, with caveats:
  - recall is **page-level**, so it overstates "did the LLM get the answer text" (q02 passes with the wrong chunk)
  - checking only `page_start` can miss chunks that span two pages
  - q01 is skipped (unanswerable); generation has to handle it later
- [ ] Stretch: recall broken out by `type` (paraphrase / identifier / keyword / distractor-bait / catalog). Prediction to test: identifier questions score worst. That's the case for hybrid search.

## Gotchas to remember

- Run from `rag/` (`cd ~/fde-lab/rag`, then `python eval.py`). Imports use the script's folder; file reads use the working directory. `BASE_DIR` handles the files.
- Ollama must be running (`search()` embeds each question).
- `json.load` (no s) = open file; `json.loads` (with s) = a string.
