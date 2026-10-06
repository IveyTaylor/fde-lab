"""
embed_corpus.py -- a script: embed every chunk once and save the vectors.

Run:  python embed_corpus.py
Needs Ollama running locally with nomic-embed-text pulled.

Reads  chunks.json / chunks_structure.json   (from build_corpus.py)
Writes embeddings.json / embeddings_structure.json
"""

import json
import time
from datetime import datetime
from pathlib import Path

from embeddings import EMBED_MODEL, EMBED_DIM, DOC_PREFIX, embed_document
from extract_chapters import is_safe_path

BASE_DIR = Path(__file__).parent


def embed_chunks(chunks_path, output_path, progress_every=50):
    """Embed every chunk record in chunks_path and write them, vectors
    attached, to output_path along with which model made them."""
    chunks = json.loads(Path(chunks_path).read_text())
    total = len(chunks)
    print(f"Embedding {total} chunks from {Path(chunks_path).name} with {EMBED_MODEL}...")

    records = []
    start = time.time()
    for i, chunk in enumerate(chunks, start=1):
        vector = embed_document(chunk["text"])

        if len(vector) != EMBED_DIM:
            raise ValueError(f"Chunk {i}: expected {EMBED_DIM} numbers, got {len(vector)}")

        records.append({**chunk, "embedding": vector})

        if i % progress_every == 0 or i == total:
            print(f"  {i}/{total}  ({time.time() - start:.0f}s)")

    output = {
        "model": EMBED_MODEL,
        "dim": EMBED_DIM,
        "doc_prefix": DOC_PREFIX,
        "source_chunks": Path(chunks_path).name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "count": len(records),
        "records": records,
    }

    if not is_safe_path(output_path, BASE_DIR):
        raise ValueError(f"Refusing to write outside {BASE_DIR}: {output_path}")

    Path(output_path).write_text(json.dumps(output))
    print(f"Wrote {len(records)} embedded chunks to {Path(output_path).name}\n")


if __name__ == "__main__":
    for chunks_name, out_name in [
        ("chunks_structure.json", "embeddings_structure.json"),
        ("chunks.json", "embeddings.json"),
    ]:
        embed_chunks(BASE_DIR / chunks_name, BASE_DIR / out_name)
