## Things I learned from 30 minutes wrestling with Claude and Python:
You always need to do this trick to get relative path:
BASE_DIR = Path(__file__).parent.resolve()
pdf_path = BASE_DIR / "corpus" / "faa" / "dot_69879_DS1.pdf"

Also, there's a default Python set up in Windows that people don't usually use, but ti's the first in the Path variable. It doesn't have anything imported, so if you happen to drop into that Python nothing works. Do a BASH where python
![
    
](image.png)

**PDF column extraction — pypdf visitor_text approach (Sept 22).** Initial
naive extraction (page.extract_text()) interleaves/merges two-column
FAA circular text unpredictably; not usable as-is for chunking.

Built extract_two_column_text() using pypdf's visitor_text hook (per-
fragment x/y via the text matrix) rather than switching to pymupdf/
pdfplumber -- avoids a new dependency, works directly off pypdf's own
positioning data.

**Real bug found and fixed:** first version split columns at page
midpoint (page.mediabox.width / 2). Seemed like a good idea at first, but 
I verified via direct fragment
logging that this is wrong for this document -- the actual column
gutter sits left of the true page midpoint, so genuine right-column
text was being misclassified into the left bucket. Fixed by computing
the gutter from the fragments' own starting-x clustering (bucket by x,
take the two most common buckets, split at their midpoint) rather than
assuming page geometry.

**Known limitations, deliberately not chased further:**
- A handful of fragments in one paragraph have stale/incorrect
  position data straight from pypdf itself (confirmed by logging --
  five different fragments reporting identical x/y). No threshold
  choice fixes wrong input data.
- Headings/captions/page numbers get sorted into whichever of the two
  buckets their x falls on, then glued to the end of that bucket's
  text -- so they can land far from their true position in reading
  order. Inherent to the two-bucket design, not fixable by tuning the
  gutter.
- Tested against one PDF (Aviation Weather ch. 9-11) so far, not the
  full FAA corpus. Revisit if retrieval eval quality suggests it
  matters; not worth generalizing further speculatively.

***********************************************************************
Heres the JSON source for the rest of the section:
  {
    "text": "Subject:1. PURPOSE. This advisory circular contains acceptable methods for\ntesting altimeters and static systems. It also provides general\ninformation concerning the test equipment used and precautions to\nbe taken when performing such tests.\n2. CANCELLATION. Advisory Circular No. AC 43-203A dated 6/6/67 is\ncanceled.\n3. RELATED PUBLICATIONS.\n43.3 and.43.5; FAR Part 91, Section 91.170; FAR Part 145, Section 145.47.\nof Atmospheric Preasure Instruments.\n4. GENERAL. Certain aircraft are required by Section 91.170 of the FAR\nto have altimeter and static system tests. These tests are described in\nAppendix E of Part 43 of the FAR. Equipment, materials, and required tests\nfor test equipment are specified in Section 145.47 of the FAR. Persons\nauthorized to perform altimeter and. static systems tests are identified in\nSection 91.170 of the FAR.\n5. STATIC PRESSURE SYSTEM TEST. Performance of thia test with all atatic\ninstruments connected will assure that leaks have not been introduced at\ninstrument connections. Use of the follOWing procedures is satisfactory as\na means for compliance with the s",
    "source_file": "dot_71398_DS1.pdf",
    "source_url": null,
    "citation_url": null,
    "page_start": 1,
    "page_end": 1,
    "chunk_index": 0,
    "chunk_size": 1000,
    "overlap": 100,
    "char_count": 1100
  },


  When a RAG gives a bad answer, it is usually one of 3 things:
  1. Extraction
  2. Chunking
  3. Retrieval

  4. generation (maybe extraction and chunking work fine but the model does something wrong)
  5. bad source (the document itself could be wrong)

  We had 4 problems in one chunk:
  1. missing text
  2. badly read OCR text
  3. cut mid-word
  4. line wraps didnt match the source

  Item 1 and 2 are problems with Extraction
  Item 3 can be fixed by a better chunker
  Item 4 can (mostly) be fixed by a better chunker
***********************************************************************

find_gutter: treat close margins as indent, not second column.
The problem was that our extractor was misreading single-column pages, 
and that has been fixed by setting a parameter:
if the margins are separated by less than the ratio (currently 0.30), it's one column
 if right_margin - left_margin < page_width * MIN_SEPARATION_RATIO:
        return float("inf")
        