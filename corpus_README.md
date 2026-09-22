# Corpus sources

This directory (`corpus/`) is excluded from git — see `.gitignore`. It's
large, and everything in it is reproducible from public sources, so the
data itself doesn't need to be version-controlled. This file records where
each piece came from and how to rebuild it.

## corpus/faa/ — FAA Advisory Circulars

Public domain (US government works). Chosen to mirror the shape of a
regulated-industry SharePoint site: genuinely messy, decades of
inconsistent formatting, some circulars scanned rather than text-native.

- Source: FAA Advisory Circulars, ROSA P
  https://rosap.ntl.bts.gov/collection_faacirculars
- Alternate browse view, if the faceted collection page misbehaves:
  https://rosap.ntl.bts.gov/cbrowse?maxResults=100&parentId=dot%3A65448&pid=dot%3A65448
- First batch pulled Sept 16, 2026.
- Known gotcha: the FAA reissues some circulars annually/periodically —
  "Advisory Circular Checklist" and "Status of Federal Aviation
  Regulations" recur across years and aren't new content. Check before
  assuming a fresh download adds topical coverage.

**Aviation_Weather_Chapters9_11.pdf** — TODO: record where this specific
excerpt was pulled from. Not captured anywhere in my notes, so this one
needs filling in from memory before it's truly reproducible.

## Ham Radio Stack Exchange data dump

Chosen as the "IntelliCentral ticket" mirror — real technical Q&A with
identifier-heavy content (equipment models, frequency bands, regulatory
tags) meant to stress-test retrieval the way exact part numbers or
regulation citations would.

- Source: Stack Exchange Data Dump on archive.org
  https://archive.org/details/stackexchange
- File: `ham.stackexchange.com.7z` (~17.4MB)
- Direct download: https://archive.org/download/stackexchange/ham.stackexchange.com.7z
- 14,084 posts, 4,734 questions, ~49% with an accepted answer
- Picked over IoT Stack Exchange (also verified; kept as a backup corpus)
  for volume, free ground-truth coverage via accepted answers, and closer
  domain fit to a regulated support environment.

## Regenerating

Re-download from the sources above. As of Sept 2026, sandboxed Claude
sessions can't reach archive.org or faa.gov directly (outbound fetch
blocked at the proxy layer) — downloads have to happen from a local
machine, not from inside a Claude session, if that's still the case
when this gets rebuilt.