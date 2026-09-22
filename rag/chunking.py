from pathlib import Path
from pypdf import PdfReader

BASE_DIR = Path(__file__).parent.parent.resolve()

def is_safe_path(target_path, base_dir):
    """
    Returns True only if target_path resolves to somewhere inside
    base_dir. Rejects '../' traversal attempts and similar tricks.
    """
    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()
    return target.is_relative_to(base)

def fixed_size_chunk(text, chunk_size, overlap):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size + overlap])
        start += chunk_size
    return chunks

def extract_two_column_text(pdf_path, page_indices=None):
    reader = PdfReader(pdf_path)
    pages = reader.pages if page_indices is None else [reader.pages[i] for i in page_indices]

    all_pages_text = []
    for page in pages:
        midpoint = float(page.mediabox.width) / 2
        left, right = [], []

        def visitor(text, cm, tm, font_dict, font_size):
            if not text.strip():
                return
            x = tm[4]  # x-position where this text fragment was drawn
            (left if x < midpoint else right).append(text)

        page.extract_text(visitor_text=visitor)
        all_pages_text.append("".join(left) + "\n" + "".join(right))

    return "\n\n".join(all_pages_text)

if __name__ == "__main__":
    input_file = BASE_DIR / "corpus" / "faa" / "Aviation_Weather_Chapters9_11.pdf"
    
    full_text = extract_two_column_text(input_file)

    chunks = fixed_size_chunk(full_text, chunk_size=1000, overlap=100)
    for c in chunks[:3]:
        print(c)


