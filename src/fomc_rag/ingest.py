"""Turn discovered meetings into parsed Documents: one statement each, plus minutes when they exist."""

import logging
import time
from pathlib import Path

from fomc_rag.discover import discover_meetings
from fomc_rag.fetch import fetch_cached
from fomc_rag.models import Document, Meeting
from fomc_rag.parse import parse_minutes, parse_statement

logger = logging.getLogger(__name__)


def ingest_meeting(meeting: Meeting, cache_dir: Path) -> list[Document]:
    """Fetch and parse one meeting into its statement Document, plus its minutes Document when minutes exist."""
    html = fetch_cached(meeting.statement_url, cache_dir)
    documents = [parse_statement(html, meeting.meeting_date, meeting.statement_url)]
    if meeting.minutes_url is not None:
        minutes_html = fetch_cached(meeting.minutes_url, cache_dir)
        documents.append(
            parse_minutes(
                minutes_html,
                meeting.meeting_date,
                meeting.minutes_url,
            )
        )
    return documents


def ingest(start_year: int, cache_dir: Path) -> list[Document]:
    """Discover meetings from start_year onward and parse them all into Documents, raising on any duplicate doc_id."""
    meetings = discover_meetings(start_year, cache_dir)
    documents: list[Document] = []
    for meeting in meetings:
        documents.extend(ingest_meeting(meeting, cache_dir))
    ids = [d.doc_id for d in documents]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate doc_id in ingested documents")
    logger.info("Ingested %d documents from %d meetings", len(documents), len(meetings))
    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start = time.perf_counter()
    documents = ingest(start_year=2019, cache_dir=Path("data/raw"))
    print(len(documents), f"{time.perf_counter() - start:.1f}s")
