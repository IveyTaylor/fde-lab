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

**** Important lesson about cosine
cosine measures "are these the same topic", not "does this answer the question"
I was asking how often do you have to check the altimeter, and it got .81 with a passage about altimeter regulations, NOT a
direct answer to the question.

Also, what about a chunk that has several different topics in it? "I like chocolate, cats are mammals, Greece is a sunny country" has
several different ideas, and the vector would be an average of all 3--this is called DILUTION. This is exactly why structure-aware 
chunking is so important. If you grab paragraphs together you have a better chance at accurate vectors, hence better chance right answers.

Weakness of vector search: keywords
I looked for "AC 43-203B", and didn't get anything for that keyword (even tho the keyword IS in the corpus), but DID get AC 43-203A. 
This is because vector search doesn't look for keywords, and a pure vector search found that the chunk 203A lives in to be closer than any chunks 203B lives in.
  This is why you need to build a hybrid-retrieval solution, that's coming soon

(Claude's version of what I said about cosine above)
### Weakness of vector search: identifiers (q02, Oct 7)
Searched "What does AC 43-203B cover?" Top result was the "2. CANCELLATION ... AC 43-203A
is canceled" chunk -- which is FROM the 203B doc (dot_71398). Right document, wrong chunk.
203B IS in the corpus (6 chunks: the cover page, page footers, and the checklist on dot_67925 p.55).

Why: to an embedding, "203A" and "203B" mean nearly the same thing -- it doesn't treat that
last letter as important. Made worse by our data:
  - the chunk that actually says "AC 43-203B" is full of OCR junk, which dilutes its vector
  - the other 203B mentions are buried in footers of chunks about other topics
Keyword search would match "203B" exactly. That's why hybrid retrieval (vector + keyword) is next.

Eval caveat: q02 will score as a HIT, because the CANCELLATION chunk is on page 1 and the
eval is labeled by page. Page-level labels can pass the wrong chunk. Spot-check the text on hits.

One limitation:
Recall@5 is page-level: it measures whether a human could find the answer, and overstates whether the LLM got the answer text.
  We are going to fix this later on

****  
## Results of Evaluation
Both chunking models (the structured and fixed) scored 19/20 correct. However, it was an eval that isn't great at separating models, because 80% of the chunks were from one file, and getting answers from a small file are easy.  

Recall@5 = .95 is a low bar for a 20 question eval set on 6 documents.

I'll need to get better data from Intellisoft, rechunk a bunch of them and do another eval. This should give a much better delta between (hopefully) fixed and structured, with structured winning.

### metadata filtering notes under Evaluation
    question = "What does AC 43-203B cover?"

Boilerplate sections act as "magnets". They have a lot of terms that are repeated and are searched for, like titles, tables of contents, etc. They are almost always false positives.

The checklist considers the top k (in this case 5). I did an experiment on a known question, with the right file, a wrong file, and no filter (all 6 files). Only the right file got the right answer to show up in the top 5.

A few answers had close to the same text, for instance one that had AC 43-203A showed up, but that doesn't help us here.

## Oct 31 — identifier harvest (step 1 of Nov 8 gate)

**What I did**
- Built `rag/term_counts.py`: list of (term, expected_source) tuples, case-insensitive
  substring match against every chunk in chunks.json, prints count per term (zeros
  visible) and each match's source/page with an expected-source check, plus context
  snippets.
- Harvested 15 candidate identifiers across 5 of 6 docs. Sorted by chunk count:
  - unique: rvr 4000, RVRNO
  - few: Frayser, 43-2a, 91.170, ac 91-32, ac 00-13
  - many: checklist office codes (afs-630 = 60 chunks). Most dropped; nobody asks a bot about office codes.

**Findings**
- AC 00-45 appears in three forms in the extracted text:
  - AW p.12: "AC 00-45" (clean)
  - AW p.15: "AG 00-45" (text layer wrong; PDF shows AC; small caps)
  - checklist p.11/57/73: "00-45D" (no AC prefix, revision suffix)
  Searching "ac 00-45" finds 1 of 5; "00-45" finds all 5.
- What I see in the PDF isn't necessarily what's in the index. "A C 00-45" (as I read it
  in the viewer) matched 0 chunks. Harvest from chunk text, not the PDF.
- Substring matching has no boundaries: "170" matched 13 chunks, mostly not 91.170.
- Checklist p.57 is a flattened table (columns interleaved). Extraction failure, same as
  the dot_67915 RVR table.
- 91.170 "in dot_72241" was my harvesting mislabel, not extraction. Checked the cheap
  explanation first.
- My own expected_source strings failed like identifiers: "chapters_9" vs "Chapters9",
  plus a typo. One-character differences break exact matching, in my test data too.
  My lesson here is to copy, don't type.
- The intent of a question decides the right chunk, not the identifier. "What covers X" →
  content page; "how do I order X" → checklist entry. Same term, different answer. I hope
  that the LLM interacting with the questioner will choose the right of the top 5 answers.

**Design questions for the keyword layer**
- Match the whole query string, or extract the identifier (e.g. "00-45") from the query?
- Word boundaries kill "170"→"1700" noise but also miss "00-45D". Pick a rule and say why.
- Case: lowercase both sides (decided). This was a good practice for me in doing lowercase
- for both sides of the equation. "CaseWord".lower() = "cASewOrd".lower()

**Question shortlist (not written yet)**
rvr 4000; RVRNO; Frayser; 43-2a; 91.170; ac 91-32 or ac 00-13;
7a AC 00-45 turbulence intensities (AW p.12); 7b AC 00-45 icing table (AW p.15, AG error);
8 AC 00-45 price/ordering (checklist p.73). Write each with a label and vector/hybrid
predictions. Commit before building the keyword layer.

### ran the eval against the chunks_structure.json 
basically got the same answers
the differences are due to overlap differences from the way chunks are chunked

ran eval.py after the page range fix and still 20/21 for both chunking schemes

## Vector search vs Hybrid tips
exact strings carry almost no weight with vector search. It's good at finding meaning, not 
good at finding strings.
For instance, looking for RVR 4000 is a risk to vector search, but I feel good about hybrid

Ask yourself 3 questions to get a good question for vector/hybrid search:
1. How many chunks have the topic?
2. What makes the RIGHT chunk different from the wrong chunks?
3. How many chunks contain the exact term?

  For RVRNO:
  1. Lots
  2. The question: "What does it mean when RVR is reported as RVRNO?" in fact DOES separate
      most of the chunks from the RIGHT chunk (so lean yes on vector). 
  3.  Only 1, The exact string is only in one chunk, so confident HIT with hybrid

For the Robert Frayser carbon monoxide cautionary tale, there are 2 chunks that both might
seem to answer the question "Why did Robert Frayser's plane go down?" The first one is he
told folks he fell asleep, but the seoncd one is the real answer--he had a carbon monoxide
leak and THAT caused him to fall asleep.

## What causes questions to "miss"
1. Only the string and no other "topic words" in the question to work with. 
    "What does AC-113 cover?"
2. The right chunk has lookalike neighbors very similar. 
    RVR 4000 is close to RVR 2000
3. The right chunk is garbled by ingestion/OCR
4. One big document crowds the top 5

## 3 Decisions about the keyword searching layer
1. Match only the identifier (identifier is the proper term for what I think of as keyword). Returns a list so more than one keywords is possible.
2. Boundary Rule: build B first, then test against A with an eval:
  A. Graded: For text just before or after the identifier, we will return it but will give more weight to the identifier with a space before and after.
  B. Rule-based: text attached AFTER will be considered (405B is a revision of 405). A digit or / attached BEFORE will not be returned. Anything else before or after (space, paren, commas, etc) is fine
3. Chunk Score: binary or weighted (weighted means more recurrances scores more)
  Let's go with binary and let vector score break the tie between multiple chunks that keyword search returns a hit for.


