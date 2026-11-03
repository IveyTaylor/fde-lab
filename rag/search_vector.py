import json
from pathlib import Path
from embeddings import EMBED_MODEL, embed_query, cosine, EMBED_DIM

BASE_DIR = Path(__file__).parent

def load_index(path):
    """Load an embeddings file written by embed_corpus.py.
    Checks it's usable, then returns the list of records."""
    path = Path(path) 
    data = json.loads(path.read_text(encoding="utf-8"))

    # 1. Same model as the one we'll embed questions with?
    if data["model"] != EMBED_MODEL:
        raise ValueError(
            f"{path.name} was embedded with {data['model']}, "
            f"but embeddings.py uses {EMBED_MODEL}. Re-run embed_corpus.py."
        )

    records = data["records"]

    # 2. Header count matches the rows actually in the file?
    if len(records) != data["count"]:
        raise ValueError(
            f"{path.name}: header says {data['count']} records, file has {len(records)}"
        )

    # 3. Every vector the right length?
    bad = [i for i, r in enumerate(records) if len(r["embedding"]) != EMBED_DIM]
    if bad:
        raise ValueError(f"{path.name}: {len(bad)} records have the wrong vector size, e.g #{bad[0]}")

    print(f"Loaded {len(records)} records from {path.name} ({data['model']}, {EMBED_DIM} dims)")
    return records

def search(question, records, k=5, source_file=None):
    q_vec = embed_query(question)
    scored = []
    if source_file is not None:
        records = [r for r in records if r["source_file"] == source_file]

    for r in records:
        score = cosine(q_vec, r["embedding"])
        scored.append((score, r)) 

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:k]  

if __name__ == "__main__":
    records = load_index(BASE_DIR / "embeddings_structure.json")

    question = "What does AC 43-203B cover?"
    #question = "What do you do when you run into turbulence?"

    for label, src in [("unfiltered", None),
                        ("right file", "dot_71398_DS1.pdf"),
                        ("wrong file", "dot_39153_DS1.pdf")]:
            print(f"\n=== {label} ===")
            for score, r in search(question, records, source_file=src):
                preview = r["text"][:80].replace("\n", " ")
                print(f"{score:.3f} | {r['source_file']} p.{r['page_start']} | {preview}")
