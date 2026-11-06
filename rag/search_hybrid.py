import search_vector
import search_keyword
from pathlib import Path

BASE_DIR = Path(__file__).parent

question = "What does AC 43-203B cover?"
records = search_vector.load_index(BASE_DIR / "embeddings.json")

#(old)results_v = search_vector.search(question, records)
# vector: score ALL chunks once, keep the top 5 for fusion
all_v = search_vector.search(question, records, k=len(records))
results_v = all_v[:5]


# keyword: unranked matches
results_k = search_keyword.search(question, records)

# lookup: (source_file, chunk_index) -> cosine score
cos = {}
for score, r in all_v:
    key = (r["source_file"], r["chunk_index"])
    cos[key] = score

# tie-break (Decision 3): order keyword matches by cosine, best first
results_k = sorted(results_k, key=lambda r: cos[(r["source_file"], r["chunk_index"])], reverse=True)

scores = {}

# pass 1: vector
for rank, (score, r) in enumerate(results_v, start=1):
    key = (r["source_file"], r["chunk_index"])
    scores[key] = scores.get(key, 0) + 1 / (60 + rank)

# pass 2: keyword
for rank, r in enumerate(results_k, start=1):
    key = (r["source_file"], r["chunk_index"])
    scores[key] = scores.get(key, 0) + 1 / (60 + rank)

ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
for key, value in ranked:
    print(key, round(value, 4))

