import json
from pathlib import Path
from search_vector import load_index, search
import search_vector
import search_hybrid

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
            if r["source_file"] == e["source_file"] and any(r["page_start"] <= p <= r["page_end"] for p in e["pages"]):
                return True                          # found a match, stop looking
    return False                                     # checked everything, no match

def run_eval(records, questions, label, search_fn):
    hit_count = 0
    scored = 0    
    print(f"\n=== {label} ===")          # ← new: blank line, then the label
    for question in questions:
        if question["type"] == "unanswerable":
            continue
        else:
            results = search_fn(question["question"], records)
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
    records_fixed = search_vector.load_index(FIXED_INDEX)
    records_structure = search_vector.load_index(STRUCTURE_INDEX)
    vector_fixed = run_eval(records_fixed, questions, "vector fixed", search_vector.search)
    vector_structure = run_eval(records_structure, questions, "vector structure", search_vector.search)
    hybrid_fixed = run_eval(records_fixed, questions, "hybrid fixed", search_hybrid.search)
    hybrid_structure = run_eval(records_structure, questions, "hybrid structure", search_hybrid.search)
    print(f"\nhybrid vs vector, fixed:     {hybrid_fixed - vector_fixed:+.2f}")
    print(f"hybrid vs vector, structure: {hybrid_structure - vector_structure:+.2f}")
