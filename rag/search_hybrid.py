import search_vector
import search_keyword
from pathlib import Path

BASE_DIR = Path(__file__).parent
VECTOR_DEPTH = 5

question = "What does AC 43-203B cover?"
records = search_vector.load_index(BASE_DIR / "embeddings.json")

def search(question, records, k=5):
    all_v = search_vector.search(question, records, k=len(records))
    results_v = all_v[:VECTOR_DEPTH]
    results_k = search_keyword.search(question, records)

    cosine_by_key = {}
    record_by_key = {}
    for score, r in all_v:
        key = (r["source_file"], r["chunk_index"])
        cosine_by_key[key] = score
        record_by_key[key] = r

    # tie-break (Decision 3): order keyword matches by cosine, best first
    results_k = sorted(results_k, key=lambda r: cosine_by_key[(r["source_file"], r["chunk_index"])], reverse=True)

    scores = {}

    # pass 1: vector
    for rank, (score, r) in enumerate(results_v, start=1):
        key = (r["source_file"], r["chunk_index"])
        scores[key] = scores.get(key, 0) + 1 / (60 + rank)

    # pass 2: keyword
    for rank, r in enumerate(results_k, start=1):
        key = (r["source_file"], r["chunk_index"])
        scores[key] = scores.get(key, 0) + 1 / (60 + rank)

    ranked = sorted(scores.items(), key=lambda kv: (kv[1], cosine_by_key[kv[0]]), reverse=True)
    for key, value in ranked:
        print(key, round(value, 4))

    return [(value, record_by_key[key]) for key, value in ranked[:k]]

if __name__ == "__main__":
    records = search_vector.load_index(BASE_DIR / "embeddings.json")
    for score, r in search("What does AC 43-203B cover?", records):
        print(f"{score:.4f} | {r['source_file']} chunk {r['chunk_index']} p.{r['page_start']}")
        