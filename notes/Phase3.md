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

Extraction: source format in, Python data out. The containers are a short list in practice:
str, list (of str's), dict (each item is text plus label, like "page number": 1, "text": "blah blah")
A good extractor doesn't just return text, it returns what it's inferred about the format, like headings, two columns, etc. It has to use regex to infer stuff.
    *You don't HAVE to do this with docs, b/c they have headings and different metadata that tells you what things are
Chunking: this DECIDES WHERE THE BOUNDARIES GO. Usually that means slicing, but sometimes it means putting little sections together.

Skew Decision: most of our chunks happened to be in one file, but that's okay, it 
mirrors reality. 

### Fixed vs. structure-aware chunking (Oct 4)

Scope: the 3 PDFs with numbered section headings (dot_71398, dot_67915, dot_72241).
The other 3 (Aviation Weather, dot_39153, the checklist) have no matching headings,
so both methods produce the same chunks there.

| Metric | Fixed | Structure |
|---|---|---|
| Chunks | 33 | 41 |
| Start at a section heading | 0 | 18 |
| Contain a heading mid-chunk (two topics mixed) | 15 | 3 |
| End mid-word (rough: last char is a letter) | 24 | 15 |
| Median size (chars) | 1,100 | 1,014 |

Per file:

| File | Fixed | Structure |
|---|---|---|
| dot_71398 | 10 | 14 |
| dot_67915 | 11 | 14 |
| dot_72241 | 12 | 13 |
| All 6 PDFs | 426 | 434 |

- The 3 mixed chunks under structure are deliberate merges of tiny sections
  (e.g. "2. CANCELLATION" + "3. RELATED PUBLICATIONS").
- The remaining mid-word cuts come from the fixed-size fallback inside long sections.
- This shows structure chunks are cleaner, not that they retrieve better.
  That gets tested by the eval at the Oct 18 gate.

*********************
Now we're into embedding. Here are 4 sentences I put into scratch.py:
sentences = [
    "The altimeter must be tested every 24 months.",
    "Altimeter and static system checks are required every two years.",
    "Keep cooking fires well clear of the helicopter landing area.",
    "How do I get to Salisbury from Charlotte?",
]
...and here are the cosines of their vectors compared to each other:
0 vs 1: 0.8340
0 vs 2: 0.4547
1 vs 2: 0.4214
0 vs 3: 0.3202
1 vs 3: 0.3162
2 vs 3: 0.3782

Note that the one about directions [3] has the lowest. Even though totally unrelated, the score "floor" is about .31.

Question and answer is the main goal in RAG. Here's how it works, user asks a question, and you compare that question to
ALL the answers (vectors) in the text...you are hoping the "right" answer (for your testing, you will already know the right
answer) is in the top 5 that your code sends back. 

If you prefix all the statements with something, all the scores will go up automatically. This is because the vectors
will get closer just based on having the same prefix.

I just finished chunking and embedding the FAA corpus...it took 58 minutes total, which is pretty slow. At this pace it would take 
about 10 hours to do 10k Intellisoft chunks. I need to figure out why this is so slow right now.

