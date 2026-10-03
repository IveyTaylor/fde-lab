import json
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from extract_chapters import is_safe_path

BASE_DIR = Path(__file__).parent
min_separation_ratio=0.30

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
    if right_margin - left_margin < page_width * min_separation_ratio:
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
        start += chunk_size
    return chunks


def pages_for_range(start, end, page_spans):
    """Which page(s) does a chunk's [start, end) character range overlap?"""
    covered = [p["page_number"] for p in page_spans if p["start"] < end and p["end"] > start]
    if not covered:
        return None, None
    return min(covered), max(covered)


def build_chunk_records(pdf_path, source_url, chunk_size=1000, overlap=100):
    """Full pipeline for one document: extract -> join with offsets ->
    chunk with offsets -> attach metadata."""
    pages = extract_two_column_pages(pdf_path)
    full_text, page_spans = join_pages_with_offsets(pages)
    chunks = chunk_with_offsets(full_text, chunk_size, overlap)

    records = []
    for i, chunk in enumerate(chunks):
        page_start, page_end = pages_for_range(chunk["start"], chunk["end"], page_spans)
        citation_url = f"{source_url}#page={page_start}" if source_url and page_start else None
        records.append({
            "text": chunk["text"],
            "source_file": Path(pdf_path).name,
            "source_url": source_url,
            "citation_url": citation_url,
            "page_start": page_start,
            "page_end": page_end,
            "chunk_index": i,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "char_count": len(chunk["text"]),
        })
    return records


def process_corpus(corpus_dir, sources_path, output_path, chunk_size=1000, overlap=100):
    """Loop every PDF in corpus_dir, skipping/logging failures instead of
    halting, and write all chunk records out as one JSON file."""
    corpus_dir = Path(corpus_dir)
    sources = json.loads(Path(sources_path).read_text()) if Path(sources_path).exists() else {}

    all_records = []
    errors = []
    for pdf_path in sorted(corpus_dir.glob("*.pdf")):
        source_url = sources.get(pdf_path.name)
        try:
            records = build_chunk_records(pdf_path, source_url, chunk_size, overlap)
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


if __name__ == "__main__":
    # single-file smoke test, matching the same input chunking.py's __main__
    # used, so the two are easy to compare while this file is still new.
    PDF_PATH = BASE_DIR.parent / "corpus" / "faa" / "Aviation_Weather_Chapters9_11.pdf"
    process_corpus(
        corpus_dir=BASE_DIR.parent / "corpus" / "faa",
        sources_path=BASE_DIR / "sources.json",   # doesn't exist yet; the code handles that and leaves citation URLs empty
        output_path=BASE_DIR / "chunks.json",     # must be inside rag/ or your safety check refuses to write it
    )
