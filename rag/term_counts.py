import json

TERMS = [
    ("Frayser",    "dot_39153_ds1.pdf"),
    ("faa-s",      "dot_67925_ds1.pdf"),
    ("atp-248a",   "dot_67925_ds1.pdf"),
    ("afs-5",      "dot_67925_ds1.pdf"),
    ("afs-630",    "dot_67925_ds1.pdf"),  # noted: lots
    ("afs-634",    "dot_67925_ds1.pdf"),  # noted: 2
    ("abc-100",    "dot_67925_ds1.pdf"),
    ("43-2a",      "dot_71398_ds1.pdf"),
    ("91.170",     "dot_71398_ds1.pdf"),
    ("ac 91-32",   "dot_72241_ds1.pdf"),
    ("ac 00-13",   "dot_67915_ds1.pdf"),
    ("rvr 4000",   "dot_67915_ds1.pdf"),
    ("RVRNO",      "dot_67915_ds1.pdf"),
    ("A C 00-45",  "aviation_weather_chapters9_11.pdf"),  # OCR spacing, kept as extracted
    ("00-45",  "aviation_weather_chapters9_11.pdf"),  
]

with open("chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)

for term, expected_source in TERMS:
    matches = [c for c in chunks if term.lower() in c["text"].lower()]
    print(term, len(matches))
    for m in matches:
        print(term, m["source_file"], expected_source, m["page_start"], m["source_file"].lower() == expected_source.lower())
        if term == "00-45":
            i = m["text"].lower().find(term.lower())
            start = max(0, i - 40)
            end = i + 40
            snippet = m["text"][start: i + len(term) + 40]
            print(snippet)
            