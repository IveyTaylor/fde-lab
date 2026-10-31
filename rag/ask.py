from pathlib import Path
from search import load_index, search

BASE_DIR = Path(__file__).parent

if __name__ == "__main__":
    records = load_index(BASE_DIR / "embeddings.json")
    while True: 
        question = input("\nQ (blank to quit): ").strip()
        if not question:
            break
        for score, r in search(question, records):
            preview = r["text"][:500].replace("\n", " ")
            print(f"{score:.3f} | {r['source_file']} p.{r['page_start']} | {preview}")
