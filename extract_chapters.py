from pypdf import PdfReader, PdfWriter
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

def is_safe_path(target_path, base_dir):
    """
    Returns True only if target_path resolves to somewhere inside
    base_dir. Rejects '../' traversal attempts and similar tricks.
    """
    base = Path(base_dir).resolve()
    target = Path(target_path).resolve()
    return target.is_relative_to(base)

def extract_pages(source_path, start_page, end_page, output_path):
    """
    Extract a page range from source_path and write it to output_path
    as a new, standalone PDF. Does not modify source_path.

    start_page and end_page are 1-indexed and inclusive, matching how
    a human reads printed page numbers (e.g. start_page=92, end_page=137
    grabs pages 92 through 137, both included).

    pypdf itself is 0-indexed internally (reader.pages[0] is page 1),
    so this function converts for you -- callers never have to think
    in 0-indexed terms.
    """
    if not is_safe_path(output_path, BASE_DIR):
        raise ValueError(f"Refusing to write outside {BASE_DIR}: {output_path}")

    reader = PdfReader(source_path)
    writer = PdfWriter()

    # convert our 1-indexed, inclusive range into the 0-indexed range
    # pypdf actually expects
    for page_number in range(start_page - 1, end_page):
        writer.add_page(reader.pages[page_number])

    with open(output_path, "wb") as output_file:
        writer.write(output_file)


if __name__ == "__main__":
    # fill these in with your own verified values before running --
    # confirm start_page/end_page against the actual PDF page index,
    # not just the printed page numbers from the table of contents
    extract_pages(
        source_path="Aviation_Weather.pdf",
        start_page=90,   # TODO: verified PDF page where Chapter 9 starts
        end_page=123,     # TODO: verified PDF page where Chapter 11 ends
        output_path="Aviation_Weather_Chapters9_11.pdf",
    )

