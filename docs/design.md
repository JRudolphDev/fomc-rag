# fomc-rag Design

## 1. Goal and scope

- **Goal:** Answer questions about FOMC outlook, policy and risk assessment, and how they changed between meetings. Every answer cites sources or says the documents don't cover it.
- **User:** Finance professionals who track Fed policy (portfolio managers, analysts, strategists, risk) and need exact wording, dates and a checkable source.
- **In scope:** FOMC statements and minutes, January 2019 onward. Single-meeting questions and comparisons across meetings.
- **Out of scope:**
  - Other Fed documents: SEP and dot plot, press conferences, speeches, Beige Book, transcripts, Statement on Longer-Run Goals.
  - Anything before 2019.
  - Predicting future decisions.
  - Economic or market data. The corpus holds the Committee's assessment, not the data.

## 2. Corpus

- **Source:** <https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>
- **Date range:** 2019 onward. Covers the 2019 cuts, the 2020 response, the 2022 hikes, later cuts and the change in Fed Chair. Older years add near-duplicate language and layout drift. Start year is a parameter.
- **Format:** HTML. Tags keep paragraphs and headings; PDF extraction loses them.
- **Discovered (Oct 2026):** 64 meetings. 2 have no minutes page (Mar 3 and Mar 23 2020).

### Data quirks

- **Dates:** Key on meeting date (last day of the meeting). Fed URLs use it (`monetary20190130a.htm`, `fomcminutes20190130.htm`). Minutes come out about three weeks later, so the newest meeting may have none yet.
- **Non-meeting statement URLs:** Match the statement pattern but are rejected by the title check.
  - Oct 11 2019: Statement Regarding Monetary Policy Implementation.
  - Mar 31 2020: FIMA repo facility.
  - Aug 27 2020 and Aug 22 2025: Statement on Longer-Run Goals.
- **Emergency meetings, 2020:** Mar 3 and Mar 23 have statements but no minutes page. Mar 3 minutes sit at the end of the Mar 15 minutes.
- **Known limitation:** Mar 3 2020 minutes are stored under Mar 15. A date filter for Mar 3 misses them.
- **Known limitation:** Minutes table content (officer roster, swap line amounts) is not parsed. Questions about those facts will miss, and the sentence that introduces a table ("the following officers... were selected:") is kept without it. See Decisions: Minutes text.
- **Two year page layouts:**
  - Historical pages (2019, 2020): link text "Statement".
  - Calendar page (2021 on): a `<strong>Statement:</strong>` label, then "PDF" and "HTML" links.
- **Statement titles:** `<title>` is "Federal Reserve Board - Federal Reserve issues FOMC statement". Note the prefix.
- **Lookalike characters:** Statement text contains U+2011 (non-breaking hyphen), which looks like `-` but is a different character. A test or keyword search for `longer-run` typed with `-` will miss it. Normalizing is decided at chunking.
- **Page scope:** Parse only inside `<div id="article">`. Site navigation is full of `<strong>` tags.
- **Statements:** No headings. Usually four to seven `<p>`: conditions, decision, guidance, vote; a few have more.
- **Minutes footnotes:** The footnote text sits in `<p>` tags at the end of the article. Each starts with an `<a name="fnN">` anchor and ends "Return to text" (6 in 2019, 8 in 2025). The markers that point to them (`<a href="#fnN"><sup>N</sup></a>`) appear in headings and mid-sentence in body text (`Cavallo,2 and`).
- **Minutes tables:** A few facts sit in `<table>` tags with no `<p>` inside: the officer roster (2019, 2025) and swap line amounts (2019). All are in Annual Organizational Matters, so January minutes only. About 550 to 700 characters per page.
- **Minutes headings:** A `<strong>` at the start of a `<p>`, then `<br />`, then the first paragraph in the same `<p>`:

  ```html
  <p><strong>Staff Review of the Financial Situation</strong><br />
  Investor risk sentiment fluctuated materially...</p>
  ```

- **Core minutes sections (all six in every minutes page, 2019 to 2026; checked on all 62):**
  1. Developments in Financial Markets and Open Market Operations (also "Discussion of Financial Markets and Open Market Operations", 2021-11-03; "Financial Developments and Open Market Operations", 2022-01-26)
  2. Staff Review of the Economic Situation
  3. Staff Review of the Financial Situation
  4. Staff Economic Outlook
  5. Participants' Views on Current Conditions and the Economic Outlook ("...on Current Economic Conditions and...", 2021-06-16 to 2021-12-15)
  6. Committee Policy Action(s) (singular in 2019, plural in 2025)
- **Heading traps:**
  - Heading and body share one `<p>`.
  - `<strong>` also marks vote labels, the date line and the signature.
  - Vote label markup varies, 2019 to 2026: colon inside the `<strong>` (`<strong>Voting for this action:</strong>`, 2019); outside it (`<strong>Voting for this action</strong>:`, 2021-12-15); mid-text with a `<br />` after, so it looks exactly like a heading (`<strong>Voting against this action: None. </strong><br />`, 2024-11-07); split across two tags (`<strong>Voting for this action</strong><strong>: </strong>`, 2026-06-17).
  - Non-core sections appear: routine (Annual Organizational Matters, Notation Vote, Attendance) and true one-offs (Long-Run Monetary Policy Implementation Frameworks in 2019; Review of Monetary Policy Strategy, Tools, and Communications in 2025).
  - Footnote markers sit inside the heading in 2025 (`<strong>Annual Organizational Matters<a href="#fn2"><sup>2</sup></a></strong>`) but after it in 2019 (`<strong>Annual Organizational Matters</strong><a href="#fn4"><sup>4</sup></a><a name="f4"></a><br />`).
  - Date line dashes vary: `January 29-30, 2019` (hyphen) vs `January 28–29, 2025` (en dash).
  - Whitespace variants (`<p><br />` before a heading, empty `<strong> </strong>`).
- **Heading rule:**
  0. **Clean once:** before the loop, remove every `<sup>` in the article. Footnote numbers then leak into neither heading text (2025 `..._2` keys) nor body text (`Cavallo, 2`). Use the markup, not a guess from the text.
  1. **Find:** a `<strong>` that is the first child of a `<p>`, skipping whitespace and `<br />`. Nothing is required after it. An earlier draft also required a following `<br />`; dropped, because in 2019 a footnote marker sits between the `</strong>` and the `<br />` (see Heading traps) and would false-reject Annual Organizational Matters.
  2. **Reject:**
     - Vote label: text starts with `Voting for`, `Voting against` or `Absent and not voting` (case-sensitive). The wording has not changed 2019 to 2026 (63, 61 and 1 occurrences, no case variants), while the markup has (see Heading traps). Rejected: "contains `:`", which would drop the real heading "Special Topic: The Standing Repo Facility" (2025-10-29). A case change would be a false accept, which WARNs.
     - Trailing colon: text ending in `:`. A backstop for a label not yet seen, logged under its own reason so it stands out at DEBUG.
     - Date line: a month name, a space, 1 or 2 digits, not followed by another digit. Matches `January 29-30` and `March 15,` whatever the dash; keeps a heading like `March 2020 Actions`.
     - A `<p>` with `text-align:center` (signature block).
     - A rejected candidate is not a heading, but its `<p>` is kept as body text in the current section: vote labels and names stay with the policy decision, the date line in the preamble, the signature in the last section.
  3. **Classify:** look up the lowercased heading in a dict of core sections and store its key: `financial_markets`, `economic_situation`, `financial_situation`, `staff_outlook`, `participants_views`, `policy_action`. Otherwise store a slug of the heading: lowercase, each run of non-alphanumeric characters becomes `_` (e.g. `annual_organizational_matters`).
     - **Known variants are data:** each wording is its own dict entry: 10 entries for 6 keys (Action and Actions; the 2021 and 2022 rewordings above). No general rule (such as stripping a trailing `s`) that would touch every heading. Exact text taken from the pages, printed with `repr` (straight apostrophe).
     - **Unseen variants rely on the WARNING:** a variant not in the dict (for example a curly apostrophe in "Participants' Views") falls through to a slug and raises the unknown-section WARNING. That is the signal to add an entry. No blanket normalization for a problem not yet seen.
- **Heading logging:** both directions, so a misclassification either way is visible.

  | Case | Level |
  | --- | --- |
  | Expected reject (vote label, trailing colon, date line, signature), with its text | DEBUG |
  | Per-document summary: section count, non-core names, reject count | INFO |
  | Known non-core heading (`KNOWN_NON_CORE`) | summary only |
  | Unknown non-core heading | WARNING |

  - **Known non-core headings (`KNOWN_NON_CORE`, 35 keys):** the 3 routine keys (`annual_organizational_matters`, `notation_vote`, `attendance`) plus the 32 one-offs and variants reviewed on the first full run (routine variants such as `notation_votes`; strategy reviews; balance sheet and repo topics; special topics).
  - **Changed from the first plan:** one-offs were to stay off the list and be added only if they recurred. The first full run then gave about 49 WARNINGs from 32 real, reviewed sections, repeated on every run. A log that always warns gets ignored, so a new false heading would be missed. Now a WARNING means a heading nobody has reviewed yet.
  - A false reject (a real heading dropped) shows at DEBUG; a false accept (junk kept as a section) shows as a WARNING.
  - Tradeoff: the set needs upkeep and grows with each new section. Each key is added once, after its warning is reviewed. `test_parse_minutes` asserts the fixtures log no WARNING.

## 3. Pipeline

Indexing (once): Ingest, Chunk, Embed, Store. Query (per question): Retrieve, Generate. Evaluate checks both.

| Stage | In | Out |
| --- | --- | --- |
| Ingest | meeting URLs | document records: IDs, date, type, URL, sectioned text. Raw HTML cached. |
| Chunk | document records | chunks: text plus section 5 metadata |
| Embed | chunk texts | one vector per chunk (Voyage, `input_type="document"`) |
| Store | vectors and metadata | persisted index behind a thin `add` / `search` interface |
| Retrieve | question | top-k chunks with scores (same model, `input_type="query"`) |
| Generate | question and labeled chunks | cited answer, or "not covered" (Claude, section 6) |
| Evaluate | test set and answers | right doc retrieved, answer correct, every citation real and supporting |

## 4. Decisions

Each decision is made when its build step arrives.

### Embeddings

- **Choice:** `voyage-4`. Dimension TODO (confirm the default, pin it).
- **Alternatives:** `voyage-4-lite`, `voyage-4-large`, `voyage-finance-2`, OpenAI `text-embedding-3-small`, local sentence-transformers.
- **Why:** Balanced quality and cost. Voyage reports the 4 series beats its finance model. The context window is long enough that chunk size is a retrieval choice, not a model limit.
- **Revisit if:** `voyage-finance-2` scores better on the test set.

### Discovery

- **Choice:** Scrape year pages. Collect every `href` matching the statement or minutes URL pattern, take the date from `YYYYMMDD` in the URL, pair by date.
- **Alternatives:** Build URLs from a list of meeting dates.
- **Why:** The URL patterns are the same in both layouts, so one rule covers every year. A date list would be hardcoded or scraped anyway, and built URLs 404 on irregular meetings.
- **Revisit if:** The Fed changes its URL patterns.

### Year page selection

- **Choice:** Fetch the calendar page first; its earliest URL year is the boundary. Use `fomchistorical{YEAR}.htm` for years from `start_year` up to the boundary.
- **Alternatives:** Hardcode the boundary; try each historical page and fall back to the calendar on a 404.
- **Why:** The boundary moves yearly as the Fed archives the oldest calendar year. Reading it from the page adjusts automatically. The 404 approach uses errors for control flow and can't tell "not archived yet" from a real failure.
- **Revisit if:** The Fed changes the calendar or historical page URLs.

### Statement filter

- **Choice:** Keep a statement only if its `<title>` ends with "Federal Reserve issues FOMC statement". No title means reject. Log every reject.
- **Alternatives:** Link-text rules per layout; `<title>` contains the phrase; `<h3>` equals the phrase.
- **Why:** One rule for every year and layout, at no extra cost since pages are fetched anyway. Strict on purpose: a false reject shows in the log, a false accept is silent.
- **Revisit if:** The log shows a real statement rejected, or a non-statement kept.

### Meeting model

- **Choice:** `Meeting` is a frozen pydantic model.
- **Alternatives:** A mutable model that fills `minutes_url` after creation.
- **Why:** A meeting is a fact from discovery. Freezing stops silent changes downstream and makes it hashable. Pairing builds a `{date: minutes_url}` dict first, so each `Meeting` is created once. Later minutes are picked up on the next run.
- **Revisit if:** A step needs to enrich meetings in place.

### Release date

- **Choice:** Not stored. Documents and chunks carry `meeting_date` only.
- **Alternatives:** Capture "(Released ...)" from year pages during discovery; parse "Last Update" from the minutes page.
- **Why:** YAGNI. Statements are released on the meeting date. Minutes release dates appear only on year pages, so capturing them changes `extract_links` and `Meeting`. "Last Update" is an update date, not a release date. Adding it later is metadata only: no change to chunk text, embeddings or IDs, just an index rebuild from the cache.
- **Revisit if:** Test questions need "what was public as of date X", or citations should show release dates.

### Statement text

- **Choice:** Keep every class-less, non-empty `<p>` inside `div#article`. Drop a `<p>` whose only content is a link to an Implementation Note (`...a1.htm`), and a `<p>` starting "For media inquiries". Keep everything else, including the vote and anything after it. Join paragraphs with a blank line. Raise `ValueError` if nothing is kept. Log both drops at DEBUG.
- **Alternatives:** Keep only paragraphs up to the vote; match boilerplate by text for both drops.
- **Why:** Surveyed all 64 statements. Header lines (date, release time) always carry a class; body paragraphs never do. The Implementation Note is detected by structure (a lone link to `a1.htm`), so a real sentence that mentions it is kept. The media line has no structural signal, so a text prefix is the only option. Stopping at the vote would drop real content in 3 statements and breaks on 4 that word the vote differently. A blank-line join keeps paragraph boundaries so chunking can still split on them.
- **Revisit if:** A new boilerplate line shows up in statement text, or the DEBUG log shows a real paragraph dropped.

### Minutes text

- **Choice:** One `Section` per accepted heading (see Heading rule), plus a `preamble` section for the text before the first heading.
  - **Preamble:** key `preamble`, heading taken from the page `<h3>` ("Minutes of the Federal Open Market Committee").
  - **Heading and body:** read the heading text from the `<strong>`, then `decompose()` it, so the rest of that `<p>` becomes the section's first paragraph.
  - **Group then build:** the loop collects raw `(key, heading, paragraphs)` groups with no empty check. One step after the loop joins each group with a blank line into a `Section` and skips empty groups. Raise `ValueError` if no section has text.
  - **Footnotes dropped:** a `<p>` that starts with an `<a name="fnN">` anchor is skipped and logged at DEBUG (see Data quirks: Minutes footnotes).
  - **Signature kept:** the centered signature lines stay at the end of the last section.
  - **Tables not parsed:** only `<p>` text is kept (see Data quirks: Minutes tables).
- **Alternatives:** Name the opening section `attendance`; build each `Section` at flush time, with the empty check in two places; keep footnotes in the last section; drop the signature with a new rule; parse tables with `get_text`.
- **Why:**
  - `preamble` names the position, not the content. In 2019 the opening is about 40 `<p>` of attendees; in 2025 it is one sentence, with a separate Attendance section. `preamble` is true every year.
  - Heading and body share one `<p>` (see Heading traps). Reading then removing the `<strong>` splits them without losing the first paragraph.
  - Group then build keeps the empty check and `Section` construction in one place: no helper, no two copies to drift.
  - Footnotes landed in the last section (Notation Vote or Attendance), so a chunk would cite them under the wrong section. The anchor is structure, so no text match is needed.
  - The signature is a few words (name, "Secretary") with no wrong-section risk worth a new rule.
  - Tables hold administrative facts only (officer roster, swap line amounts), about 550 to 700 characters in roughly 8 of 62 pages. `get_text` flattens rows and columns into hard-to-read text. The focus is monetary policy; tables can be added later if a test question needs them.
- **Revisit if:** A test question needs officer or swap line facts; the WARNING log shows a heading variant; the DEBUG log shows a real paragraph dropped as a footnote.

### IDs

- **Choice:** `doc_id` is `{doc_type}-{meeting_date}`. `chunk_id` is `{doc_id}-{position}`, zero-padded (`minutes-2022-06-15-014`).
- **Alternatives:** Section name in the chunk ID (`minutes-2022-06-15-participants-views-03`).
- **Why:** `doc_id` is unique because discovery yields one statement and at most one minutes page per date. Keeping labels out of `chunk_id` removes one class of breakage: renaming a section key or fixing the heading classifier would otherwise change IDs for identical text and break the test set. The `section` field still carries the section.
- **Revisit if:** Two documents of the same type ever share a meeting date.

### Raw data and fixtures

- **Choice:** Raw HTML cache in `data/raw/`, gitignored. A few pages committed in `tests/fixtures/`.
- **Alternatives:** Commit the full cache; commit nothing.
- **Why:** The cache is a build output one command regenerates. Fixtures keep tests offline and deterministic. Fed pages are US government works.
- **Revisit if:** The Fed site becomes unreliable to fetch.

### Cache policy

- **Choice:** Cached pages never expire. Callers pass `refresh=True` for living pages (the calendar). Writes go to a `.tmp` file, then an atomic rename. Bytes stored raw, decoded with `utf-8-sig`.
- **Alternatives:** Expire by age; conditional requests (`ETag`, `If-Modified-Since`); never cache year pages.
- **Why:**
  - Published statements and minutes don't change, so expiry adds nothing. The calendar gains meetings, so it must be fresh.
  - The caller decides because it knows which pages change; the fetcher stays generic.
  - The cache check is `exists()`, which is true for a half-written file. The atomic rename means the real path only ever holds complete files.
  - Raw bytes keep the original. `utf-8-sig` strips the BOM the Fed serves.
- **Revisit if:** A published page gets corrected, or more living pages appear.

### Ingest orchestration

- **Choice:** `ingest.py` runs discovery, then fetches and parses each meeting's statement and, when `minutes_url` is not `None`, its minutes. It stops on the first error, holds all Documents in memory, and raises if two Documents share a `doc_id`.
- **Alternatives:** Log and skip a failing meeting; write each Document to disk as it is parsed; rely on the models to catch duplicates.
- **Why:**
  - Every error raised here means the parser met markup it does not understand. Skipping would build a corpus with a meeting missing, and the later steps would run over the gap. Stopping does not depend on anyone reading the log, and a rerun from cache takes 6.1s.
  - About 127 Documents fit in memory: 6.1s from cache, 74.9s with downloads. Writing to disk would add a file format and a load step with no benefit yet.
  - Pydantic validates one object at a time, so it cannot see a duplicate across Documents. `chunk_id` is built from `doc_id`, so a duplicate would silently overwrite the first Document's chunks in the store.
- **Revisit if:** The corpus or run time grows enough that a rerun is expensive, runs become unattended, or failures that are not parser bugs (network errors) become common. Then log and skip, and report every failure at the end.

### Vector store

- **Decide when:** Before the Store step.
- **Options:** Chroma (simplest), FAISS (faster, more manual), pgvector (SQL).
- **Choice:** TODO

### Chunking

- **Decide when:** Before any chunking code. Written defense required.
- **Options:** Fixed-size with overlap, recursive sentence-aware, section-aware, semantic.
- **Evidence so far:** The six core minutes sections map to the question types in section 1. Statements are short and have no sections.
- **Open questions:** Split statements at all? Section or paragraph chunks for minutes?
- **Choice:** TODO

### Top-k

- **Decide when:** After the test set exists, by experiment.
- **Options:** k = 3, 5, 10.
- **Choice:** TODO

## 5. Chunk schema (draft)

| Field | Example | Purpose |
| --- | --- | --- |
| `chunk_id` | `minutes-2022-06-15-014` | Citation key: `doc_id` plus zero-padded position in the document |
| `doc_id` | `minutes-2022-06-15` | Source document |
| `doc_type` | `statement` / `minutes` | Filtering |
| `meeting_date` | `2022-06-15` | Links statement to minutes; date filtering |
| `section` | `participants_views` | Section filtering. Statements use `statement`: never null, so no null handling in the store, and no invented paragraph labels. |
| `url` | Fed page URL | One step from citation to source |
| `text` | chunk text | Embedded and shown to the model |

## 6. Grounding contract

1. Answer only from the provided chunks. No outside knowledge.
2. Cite a chunk ID inline for every factual claim.
3. If the chunks don't contain the answer, say so. Don't guess.
4. For comparisons, cite at least one chunk per meeting, or say which side is missing.

## 7. Test set

- **Location:** `eval/questions.jsonl`
- **Fields:** `question`, `expected_answer`, `source_doc_ids`, `category`
- **Rule:** Expected answers come from reading the documents, not memory or an LLM.
- **Categories:** Single fact, Votes, Reasoning, Paraphrase, Comparison (a minority), Unanswerable.
- **Questions:** TODO

## 8. Failure modes

| Failure | What happens | Guard |
| --- | --- | --- |
| Bad chunk boundaries | A fact split across chunks retrieves poorly | Section-aware chunking and the heading rule |
| Paraphrase misses | Question wording differs from the document | Paraphrase test category; hybrid BM25 is the stretch fix |
| Citation hallucination | A cited chunk doesn't support the claim | Readable IDs; citation checks in Evaluate |
| Answering from weights | The model knows Fed history and uses it | Rule 1; Unanswerable test questions |
