# fomc-rag Design

## 1. Goal and scope

- **Goal:** Answer questions about the FOMC's outlook, policy, and risk assessment, and how they changed between meetings. Every answer cites its sources or says the documents don't cover it.
- **User:** A portfolio analyst tracking Fed policy who needs precise wording, dates, and a checkable source.
- **In scope:** FOMC statements and minutes from January 2019 onward. Single-meeting questions and comparisons between meetings.
- **Out of scope:**
  - Other Fed documents (SEP and dot plot, press conferences, speeches, Beige Book, transcripts, Statement on Longer-Run Goals and Monetary Policy Strategy)
  - Anything before January 2019
  - Predicting future decisions
  - Economic or market data. The corpus holds the Committee's assessment of conditions, not the data.

## 2. Corpus

- **Source:** https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- **Date range:** January 2019 onward. A pre-COVID baseline that covers the 2019 cuts, the 2020 response, the 2022 hiking cycle, later cuts, and the change in Fed Chair. Older years add near-duplicate language and layout drift. Start date is a parameter.
- **Format:** HTML. Tags keep paragraphs and headings, so structure is recoverable. PDF extraction loses it.

### Data quirks

- **Two dates per document:** Key on meeting date (last day of the meeting). Store release date separately. Minutes come out about three weeks later, so the newest meeting may have no minutes yet. Fed URLs already use the meeting date (`monetary20190130a.htm`, `fomcminutes20190130.htm`).
- **2020 extra links:** 12 statement-pattern URLs, 8 minutes.
  - Mar 3 and Mar 23: emergency FOMC statements with no minutes page of their own. Mar 3 minutes are at the end of the Mar 15 minutes.
  - Mar 31 (FIMA repo facility) and Aug 27 (Statement on Longer-Run Goals): not post-meeting statements. Out of scope.
- **Known limitation, Mar 3 2020 minutes:** Stored under the Mar 15 meeting date. Affects one meeting; the text is still indexed and cites a real document. Cost: a date filter for Mar 3 misses it.
- **Two page layouts for discovery:**
  - Historical pages (2019, 2020): statement link text is "Statement".
  - Calendar page (2021 onward): a `<strong>Statement:</strong>` label, then links with text "PDF" and "HTML".
  - The calendar page also lists the 2025 Statement on Longer-Run Goals (Aug 22). Out of scope.
  - Every real post-meeting statement page has the title "Federal Reserve issues FOMC statement".
- **Page scope:** Parse only inside `<div id="article">`. The site navigation is full of `<strong>` tags.
- **Statements:** No headings. About four `<p>` paragraphs: conditions, decision, guidance, vote.
- **Minutes headings:** A `<strong>` at the start of a `<p>`, then `<br />`, then the section's first paragraph in the same `<p>`:

  ```html
  <p><strong>Staff Review of the Financial Situation</strong><br />
  Investor risk sentiment fluctuated materially...</p>
  ```

- **Core minutes sections (2019 and 2025):**
  1. Developments in Financial Markets and Open Market Operations
  2. Staff Review of the Economic Situation
  3. Staff Review of the Financial Situation
  4. Staff Economic Outlook
  5. Participants' Views on Current Conditions and the Economic Outlook
  6. Committee Policy Action(s) (singular in 2019, plural in 2025)
- **Heading traps:**
  - Heading and body share one `<p>`.
  - `<strong>` also marks vote labels, the date line, and the signature.
  - One-off sections appear (Annual Organizational Matters, Attendance).
  - Whitespace variants (`<p><br />` before a heading, empty `<strong> </strong>`).
- **Heading rule:** Three steps.
  1. **Find candidates:** A `<strong>` that is the first content of a `<p>` (ignoring whitespace and leading `<br />`), followed by `<br />`.
  2. **Reject non-headings:** Text ending in `:` after stripping (vote labels). Text that is a date (date line). A `<p>` with `text-align:center` (signature block).
  3. **Classify:** If the text matches a core section (case-insensitive, Action and Actions treated as equal), store its canonical key: `financial_markets`, `economic_situation`, `financial_situation`, `staff_outlook`, `participants_views`, `policy_action`. Otherwise store a slug of the raw heading (for example `annual_organizational_matters`) and log it for review.

## 3. Pipeline

Indexing (once): Ingest → Chunk → Embed → Store. Query (per question): Retrieve → Generate. Evaluate checks both.

- **Ingest:** meeting URLs → document records (IDs, dates, type, URL, cleaned text with sections). Cache raw HTML.
- **Chunk:** document records → chunk objects (text plus section 5 metadata).
- **Embed:** chunk texts → one vector per chunk (Voyage, `input_type="document"`).
- **Store:** vectors and metadata → persisted index behind a thin `add` / `search` interface.
- **Retrieve:** question → embed with the same model (`input_type="query"`) → top-k chunks with scores.
- **Generate:** question and labeled chunks → cited answer, or "not covered" (Claude, section 6 rules).
- **Evaluate:** test set and answers → right doc retrieved, answer correct, every citation exists and supports its claim.

## 4. Decisions

Each decision is made when its build step is reached, not up front.

### Embeddings

- **Choice:** `voyage-4`, dimension TODO (confirm default in Voyage docs)
- **Alternatives:** `voyage-4-lite`, `voyage-4-large`, `voyage-finance-2`, OpenAI `text-embedding-3-small`, local sentence-transformers
- **Why:** Balanced quality and cost. Voyage reports the 4 series beats its older finance model. Context window is long enough that chunk size is a retrieval choice, not a model limit.
- **Revisit if:** `voyage-finance-2` scores better on the test set.

### Discovery

- **Choice:** Scrape year pages. Collect every `href` matching the statement or minutes URL pattern, take the meeting date from `YYYYMMDD` in the URL, and pair statements and minutes by date.
- **Alternatives:** Build URLs from a list of meeting dates.
- **Why:** URL patterns are the same in both page layouts, so one rule covers every year. A date list would be hardcoded or scraped anyway, and built URLs 404 on irregular meetings (Mar 3 2020 has no minutes page).
- **Revisit if:** The Fed changes its URL patterns.

### Raw data and fixtures

- **Choice:** Raw HTML cache in `data/raw/`, gitignored. A few saved pages committed in `tests/fixtures/` for offline parser tests.
- **Alternatives:** Commit the full cache; commit nothing.
- **Why:** The cache is a build output that one command regenerates. Fixtures keep tests deterministic when the Fed site changes. Fed pages are US government works.
- **Revisit if:** The Fed site becomes unreliable to fetch, making a committed snapshot worth the size.

### Cache policy

- **Choice:** Cached pages never expire. The caller passes `refresh=True` for living pages (`fomccalendars.htm`), which re-downloads and overwrites. Writes go to a `.tmp` file, then rename into place. Bytes are stored raw and decoded with `utf-8-sig` on read.
- **Alternatives:** Expire by age; conditional requests (`ETag` / `If-Modified-Since`); never cache year pages.
- **Why:** Statement and minutes pages never change once published, so expiry adds nothing. The calendar page gains meetings during the year, so it must be fresh. The caller decides because it knows which pages change; the fetcher stays generic. The rename is atomic, so a crash mid-write cannot leave a truncated page that later reads as a valid cache hit. Raw bytes keep the original; `utf-8-sig` strips the BOM the Fed serves on some pages.
- **Revisit if:** A past page gets corrected after publication, or more living pages appear.

### Statement filter

- **Choice:** Title check. Keep a fetched statement candidate only if its title ends with "Federal Reserve issues FOMC statement". Log every rejected URL.
- **Alternatives:** Link-text rules per page layout.
- **Why:** One rule for every year and both page layouts. Pages are fetched and cached anyway, so the check costs nothing extra.
- **Revisit if:** The log shows a real statement rejected, or a non-statement kept.

### Year page selection

- **Choice:** Fetch `fomccalendars.htm` first and find the earliest year among its extracted URL dates. Use `fomchistorical{YEAR}.htm` for every year from `start_year` up to that one.
- **Alternatives:** Hardcode the boundary year; try the historical page per year and fall back to the calendar on a 404.
- **Why:** The boundary moves each year as the Fed archives the oldest calendar year. Reading it from the calendar page adjusts automatically. The 404 approach uses errors for control flow and cannot tell "not archived yet" from a real failure.
- **Revisit if:** The Fed changes the calendar or historicalpage URLs.

### Meeting model

- **Choice:** `Meeting` is a frozen pydantic model.
- **Alternatives:** Mutable model, filling `minutes_url` after creation.
- **Why:** A meeting is a fact from discovery. Freezing stops later steps from changing one silently and makes it hashable for sets and dict keys. Pairing builds a `{date: minutes_url}` dict first, so each `Meeting` is created once with everything known. Minutes published later are picked up on the next run, which builds new objects.
- **Revisit if:** A step needs to enrich meetings in place.

### Vector store

- **Decide when:** Before the Store step.
- **Options:** Chroma (simplest local start), FAISS (faster, more manual), pgvector (SQL around vectors)
- **Choice:** TODO

### Chunking

- **Decide when:** Before any chunking code. Written defense required.
- **Options:** Fixed-size with overlap, recursive sentence-aware, section-aware, semantic
- **Evidence so far:** Six core minutes sections map to the question types in section 1. Statements have no sections and are short.
- **Open questions:** Split statements at all? Section or paragraph chunks for minutes? Normalize headings (Action vs Actions)?
- **Choice:** TODO

### Top-k

- **Decide when:** After the test set exists. Decided by experiment.
- **Options:** k = 3, 5, 10
- **Choice:** TODO

## 5. Chunk schema (draft)

| Field | Example | Purpose |
|---|---|---|
| `chunk_id` | `minutes-2022-06-15-participants-views-03` | Citation key, readable by eye |
| `doc_id` | `minutes-2022-06-15` | Source document |
| `doc_type` | `statement` / `minutes` | Filtering |
| `meeting_date` | `2022-06-15` | Links statement to minutes; date filtering |
| `release_date` | `2022-07-06` | When it went public |
| `section` | `participants_views` | Section filtering; null for statements |
| `url` | Fed page URL | One step from citation to source |
| `text` | chunk text | What gets embedded and shown to the model |

## 6. Grounding contract

1. Answer only from the provided chunks. No outside knowledge.
2. Cite a chunk ID inline for every factual claim.
3. If the chunks don't contain the answer, say so. Don't guess.
4. For comparisons, cite at least one chunk from each meeting, or say which side is missing.

## 7. Test set

- **Location:** `eval/questions.jsonl`
- **Format:** `question`, `expected_answer`, `source_doc_ids`, `category`
- **Rule:** Expected answers come from reading the documents, not memory or an LLM.
- **Categories:** Single fact, Votes, Reasoning, Paraphrase, Comparison (minority of the set), Unanswerable
- **Questions:** TODO

## 8. Failure modes

- **Bad chunk boundaries:** A fact split across chunks retrieves poorly. Section-aware chunking and the heading rule keep related text together.
- **Paraphrase misses:** Question wording differs from the document. The paraphrase test category measures it. Hybrid BM25 is the stretch fix.
- **Citation hallucination:** A cited chunk doesn't support the claim. Readable IDs and citation checks in Evaluate catch it.
- **Answering from weights:** The model knows Fed history. Rule 1 forbids using it. Unanswerable test questions catch it.
