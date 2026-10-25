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

- **Source:** https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
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
- **Two year page layouts:**
  - Historical pages (2019, 2020): link text "Statement".
  - Calendar page (2021 on): a `<strong>Statement:</strong>` label, then "PDF" and "HTML" links.
- **Statement titles:** `<title>` is "Federal Reserve Board - Federal Reserve issues FOMC statement". Note the prefix.
- **Page scope:** Parse only inside `<div id="article">`. Site navigation is full of `<strong>` tags.
- **Statements:** No headings. About four `<p>`: conditions, decision, guidance, vote.
- **Minutes headings:** A `<strong>` at the start of a `<p>`, then `<br />`, then the first paragraph in the same `<p>`:

  ```html
  <p><strong>Staff Review of the Financial Situation</strong><br />
  Investor risk sentiment fluctuated materially...</p>
  ```

- **Core minutes sections (stable 2019 to 2025):**
  1. Developments in Financial Markets and Open Market Operations
  2. Staff Review of the Economic Situation
  3. Staff Review of the Financial Situation
  4. Staff Economic Outlook
  5. Participants' Views on Current Conditions and the Economic Outlook
  6. Committee Policy Action(s) (singular in 2019, plural in 2025)
- **Heading traps:**
  - Heading and body share one `<p>`.
  - `<strong>` also marks vote labels, the date line and the signature.
  - One-off sections appear (Annual Organizational Matters, Attendance).
  - Whitespace variants (`<p><br />` before a heading, empty `<strong> </strong>`).
- **Heading rule:**
  1. **Find:** a `<strong>` that is the first content of a `<p>` (ignoring whitespace and a leading `<br />`), followed by `<br />`.
  2. **Reject:** text ending in `:` (vote labels); text that is a date (date line); a `<p>` with `text-align:center` (signature).
  3. **Classify:** match a core section case-insensitively (Action = Actions) and store its key: `financial_markets`, `economic_situation`, `financial_situation`, `staff_outlook`, `participants_views`, `policy_action`. Otherwise store a slug of the heading (e.g. `annual_organizational_matters`) and log it.

## 3. Pipeline

Indexing (once): Ingest, Chunk, Embed, Store. Query (per question): Retrieve, Generate. Evaluate checks both.

| Stage | In | Out |
|---|---|---|
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
|---|---|---|
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
|---|---|---|
| Bad chunk boundaries | A fact split across chunks retrieves poorly | Section-aware chunking and the heading rule |
| Paraphrase misses | Question wording differs from the document | Paraphrase test category; hybrid BM25 is the stretch fix |
| Citation hallucination | A cited chunk doesn't support the claim | Readable IDs; citation checks in Evaluate |
| Answering from weights | The model knows Fed history and uses it | Rule 1; Unanswerable test questions |
