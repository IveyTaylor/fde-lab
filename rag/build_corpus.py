import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from extract_chapters import is_safe_path

BASE_DIR = Path(__file__).parent
MIN_SEPARATION_RATIO = 0.30

def find_gutter(x_positions, page_width, bucket_size=20):
    """Find the x-value that best separates the left column from the right
    column, by grouping fragment start-positions into buckets and taking
    the two most common buckets -- those are the real column margins,
    since body text repeats the same starting x line after line while
    headings/captions only contribute one-off positions.

    A page with no text, or genuinely only one column, won't have two
    distinct buckets -- fall back to +infinity so every fragment lands in
    "left" and nothing gets split. That reproduces plain single-column
    reading order instead of crashing on pages this method doesn't apply to."""
    if not x_positions:
        return float("inf")

    buckets = Counter(round(x / bucket_size) * bucket_size for x in x_positions)
    common = buckets.most_common(2)

    if len(common) < 2:
        return float("inf")

    (left_margin, _), (right_margin, _) = common
    if left_margin > right_margin:
        left_margin, right_margin = right_margin, left_margin
    # NEW: too close together = an indent, not a second column
    if right_margin - left_margin < page_width * MIN_SEPARATION_RATIO:
        return float("inf")
    return (left_margin + right_margin) / 2


def extract_two_column_pages(pdf_path, page_indices=None):
    """Returns one record per page, so page identity survives into chunking."""
    reader = PdfReader(pdf_path)
    pages = reader.pages if page_indices is None else [reader.pages[i] for i in page_indices]

    records = []
    for page_number, page in enumerate(pages, start=1):
        fragments = []

        def visitor(text, cm, tm, font_dict, font_size):
            if not text.strip():
                return
            fragments.append((tm[4], text))

        page.extract_text(visitor_text=visitor)

        gutter = find_gutter([x for x, _ in fragments], float(page.mediabox.width))
        left, right = [], []
        for x, text in fragments:
            (left if x < gutter else right).append(text)

        records.append({
            "page_number": page_number,
            "text": "".join(left) + "\n" + "".join(right),
        })

    return records


def join_pages_with_offsets(pages, separator="\n\n"):
    """Concatenate per-page text into one string, recording each page's
    character span within that string."""
    full_text_parts = []
    page_spans = []
    offset = 0

    for page in pages:
        text = page["text"]
        start = offset
        end = start + len(text)
        page_spans.append({"page_number": page["page_number"], "start": start, "end": end})
        full_text_parts.append(text)
        offset = end + len(separator)

    return separator.join(full_text_parts), page_spans


def chunk_with_offsets(text, chunk_size, overlap):
    """Fixed size slicing with overlap. Returns each chunks text plus its character range 
    so it can be mapped back to pages"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size + overlap
        chunks.append({"start": start, "end": min(end, len(text)), "text": text[start:end]})
        if end >= len(text):
            break   # this chunk reached the end; another would be pure overlap
        start += chunk_size
    return chunks


def pages_for_range(start, end, page_spans):
    """Which page(s) does a chunk's [start, end) character range overlap?"""
    covered = [p["page_number"] for p in page_spans if p["start"] < end and p["end"] > start]
    if not covered:
        return None, None
    return min(covered), max(covered)


def resolve_source(entry):
    """Normalize one sources.json value into (source_url, is_excerpt).

    sources.json allows two shapes per file:
      "file.pdf": "https://..."                          -> whole document
      "file.pdf": {"url": "https://...", "excerpt": true} -> a page-range
                                                             excerpt of that URL
    A file missing from sources.json comes in as None."""
    if entry is None:
        return None, False
    if isinstance(entry, dict):
        return entry.get("url"), entry.get("excerpt", False)
    return entry, False


def build_chunk_records(pdf_path, source_url, chunk_size=1000, overlap=100, method="fixed",
                        is_excerpt=False):
    """Full pipeline for one document: extract -> join with offsets ->
    chunk with offsets -> attach metadata.

    is_excerpt: the local PDF is a slice of the document at source_url, so
    local page numbers don't match the original. Link to the document
    itself, with no #page= anchor, rather than to a wrong page."""
    pages = extract_two_column_pages(pdf_path)
    full_text, page_spans = join_pages_with_offsets(pages)
    if method == "structure":
        chunks = chunk_by_structure(full_text, chunk_size, overlap)
    else:
        chunks = chunk_with_offsets(full_text, chunk_size, overlap)

    records = []
    for i, chunk in enumerate(chunks):
        page_start, page_end = pages_for_range(chunk["start"], chunk["end"], page_spans)
        if not source_url:
            citation_url = None
        elif is_excerpt or not page_start:
            citation_url = source_url  # whole document, no page anchor
        else:
            citation_url = f"{source_url}#page={page_start}"
        records.append({
            "text": chunk["text"],
            "source_file": Path(pdf_path).name,
            "source_url": source_url,
            "citation_url": citation_url,
            "is_excerpt": is_excerpt,
            "page_start": page_start,
            "page_end": page_end,
            "chunk_index": i,
            "method": method,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "char_count": len(chunk["text"]),
        })
    return records


def process_corpus(corpus_dir, sources_path, output_path, chunk_size=1000, overlap=100, method="fixed"):
    """Loop every PDF in corpus_dir, skipping/logging failures instead of
    halting, and write all chunk records out as one JSON file."""
    corpus_dir = Path(corpus_dir)
    sources = json.loads(Path(sources_path).read_text()) if Path(sources_path).exists() else {}

    all_records = []
    errors = []
    for pdf_path in sorted(corpus_dir.glob("*.pdf")):
        source_url, is_excerpt = resolve_source(sources.get(pdf_path.name))
        try:
            records = build_chunk_records(pdf_path, source_url, chunk_size, overlap, method,
                                          is_excerpt=is_excerpt)
            all_records.extend(records)
            print(f"OK   {pdf_path.name}: {len(records)} chunks")
        except Exception as e:
            errors.append((pdf_path.name, str(e)))
            print(f"FAIL {pdf_path.name}: {e}")

    if not is_safe_path(output_path, BASE_DIR):
        raise ValueError(f"Refusing to write outside {BASE_DIR}: {output_path}")

    Path(output_path).write_text(json.dumps(all_records, indent=2))
    print(f"\nWrote {len(all_records)} chunk records from {len(list(corpus_dir.glob('*.pdf'))) - len(errors)} files to {output_path}")
    if errors:
        print(f"{len(errors)} file(s) failed: {[name for name, _ in errors]}")

# A numbered ALL-CAPS heading like "1. PURPOSE." or "3. RELATED PUBLICATIONS."
# Lookbehind: preceded by whitespace (or start of text), not necessarily a
# newline, because fragments are joined with "" and many headings sit mid-line.
# Lookahead: match the position *before* the heading, without consuming it.
HEADING_RE = re.compile(r"(?:^|(?<=\s))(?=\d{1,2}\.\s+[A-Z]{2,}[A-Z ,'()/-]*\.)")

def chunk_by_structure(text, chunk_size, overlap, min_size=200):
    """Split at numbered section headings; merge tiny sections forward;
    fall back to fixed-size slicing inside any section that's too big.
    Same {start, end, text} output shape as chunk_with_offsets."""
    max_size = chunk_size + overlap #match fixed_size's real chunk length

    # 1. Cut points: start fo text, every heading, end fo text
    cuts = [0] + [m.start() for m in HEADING_RE.finditer(text) if m.start() > 0] + [len(text)]
    sections = [(a, b) for a, b in zip(cuts, cuts[1:]) if text[a:b].strip()]

    # 2. Merge: if the previous section is tiny, absorb this one into it.
    merged = []
    for a, b in sections:
        if merged and merged[-1][1] - merged[-1][0] < min_size:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))

    # 3. Emit sections; split oversize ones with the fixed-size chunker,
    #    shifting its offsets from section-relative back to full_text-relative.
    chunks = []
    for a, b in merged:
        if b - a <= max_size:
            chunks.append({"start": a, "end": b, "text": text[a:b]})
        else:
            for c in chunk_with_offsets(text[a:b], chunk_size, overlap):
                chunks.append({"start": a + c["start"], "end": a + c["end"], "text": c["text"]})
    return chunks

if __name__ == "__main__":
    for method, out_name in [("fixed", "chunks.json"), ("structure", "chunks_structure.json")]:
        print(f"\n=== {method} ===")
        process_corpus(
            corpus_dir=BASE_DIR.parent / "corpus" / "faa",
            sources_path=BASE_DIR / "sources.json",
            output_path=BASE_DIR / out_name,
            method=method,
        )
