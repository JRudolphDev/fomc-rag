from datetime import date
from pathlib import Path

from fomc_rag.ingest import ingest_meeting
from fomc_rag.models import Meeting

FIXTURES = Path(__file__).parent / "fixtures"
STATEMENT_URL = (
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250129a.htm"
)
MINUTES_URL = "https://www.federalreserve.gov/monetarypolicy/fomcminutes20250129.htm"


def test_ingest_meeting_with_minutes(no_network):
    meeting = Meeting(
        meeting_date=date(2025, 1, 29),
        statement_url=STATEMENT_URL,
        minutes_url=MINUTES_URL,
    )
    documents = ingest_meeting(meeting, FIXTURES)
    assert [d.doc_id for d in documents] == [
        "statement-2025-01-29",
        "minutes-2025-01-29",
    ]


def test_ingest_meeting_without_minutes(no_network):
    meeting = Meeting(
        meeting_date=date(2025, 1, 29),
        statement_url=STATEMENT_URL,
        minutes_url=None,
    )
    documents = ingest_meeting(meeting, FIXTURES)
    assert [d.doc_id for d in documents] == ["statement-2025-01-29"]
