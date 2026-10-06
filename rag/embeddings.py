"""
embeddings.py -- shared embedding tools (a module: import it, don't run it).

Everything that turns text into vectors, or compares vectors, lives here so
the corpus script and the search script are guaranteed to use the SAME model
and the SAME prefixes. Vectors from different models (or different prefixes)
are not comparable -- the scores come out, they just mean nothing.
"""

import math

import requests

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"   # change this => re-run embed_corpus.py
EMBED_DIM = 768                    # what nomic-embed-text returns

# nomic-embed-text is trained to expect a task prefix on every input.
DOC_PREFIX = "search_document: "   # for chunks being stored
QUERY_PREFIX = "search_query: "    # for questions being searched


def embed(text):
    """Send one string to the local embedding model; return its vector (a list of floats).
    Low-level: sends the text exactly as given. Prefer embed_document / embed_query."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    response.raise_for_status()                 # turn an HTTP error into a Python error
    return response.json()["embeddings"][0]     # list of lists -> take the first (only) one


def embed_document(text):
    """Embed a chunk for storage (adds the document prefix)."""
    return embed(DOC_PREFIX + text)


def embed_query(text):
    """Embed a user question for searching (adds the query prefix)."""
    return embed(QUERY_PREFIX + text)


def cosine(a, b):
    """Cosine similarity: 1.0 = same direction, ~0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)

if __name__ == "__main__":
    """This is for testing purposes only. __main__ is being used here to practice on a 
    very small corpus to make sure sentence 0 shows up as the best answer to sentenct 3
    """
    PAIRS = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3)]
    sentences = [
    "The altimeter must be tested every 24 months.",
    "Altimeter and static system checks are required every two years.",
    "Keep cooking fires well clear of the helicopter landing area.",
    "How often does the altimeter need to be tested?",
    ]
    v_embed = [embed(s) for s in sentences]
    v_embed_document = [embed_document(s) for s in sentences]
    v_embed_query = [embed_query(s) for s in sentences]
    for s, v in zip(sentences, v_embed):
        print(f"min {min(v):.3f}  max {max(v):.3f}  | {s}")

    for j in [0, 1, 2]:
        score = cosine(v_embed_query[3], v_embed_document[j])
        print(f"Q vs {j}: {score:.3f}")

