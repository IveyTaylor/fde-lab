import json
from pathlib import Path
from search import load_index, search

BASE_DIR = Path(__file__).parent
QUESTIONS_PATH = BASE_DIR / "eval_questions.jsonl"
FIXED_INDEX = BASE_DIR / "embeddings.json"
STRUCTURE_INDEX = BASE_DIR / "embeddings_structure.json"

def load_questions(path):
    """Read a .jsonl file (one JSON object per line). Return a list of dicts."""
    text = Path(path).read_text(encoding="utf-8")   # whole file as one string
    questions = []
    for line in text.splitlines():                  # break the string into lines
        if not line.strip():                        # blank line? skip it
            continue
        questions.append(json.loads(line))          # parse ONE line -> one dict
    return questions

def is_hit(results, expected):
    """True if any search result lands on an expected file + page."""
    for score, r in results:                         # each of the top-k results
        for e in expected:                           # each acceptable answer location
            if r["source_file"] == e["source_file"] and r["page_start"] in e["pages"]:
                return True                          # found a match, stop looking
    return False                                     # checked everything, no match

def run_eval(records, questions, label):
    hit_count = 0
    scored = 0    
    print(f"\n=== {label} ===")          # ← new: blank line, then the label
    for question in questions:
        if question["type"] == "unanswerable":
            continue
        else:
            results = search(question["question"], records)
            hit = is_hit(results, question["expected"])
            if hit: 
                hit_count += 1
            scored += 1
            print("HIT" if hit else "miss", question["id"], question["type"], question["question"])
    print(f"Eval complete for {label}: hit {hit_count} of {scored} scored")
    recall = hit_count / scored
    print(f"{label}: recall@5 = {hit_count}/{scored} = {recall:.2f}")
    return recall

if __name__ == "__main__":
    questions = load_questions(QUESTIONS_PATH)
    records_fixed = load_index(FIXED_INDEX)
    records_structure = load_index(STRUCTURE_INDEX)
    fixed = run_eval(records_fixed, questions, "fixed")
    structure = run_eval(records_structure, questions, "structure")
    print(f"\nstructure vs fixed: {structure - fixed:+.2f}")
