from datetime import date
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from fomc_rag.parse import is_implementation_note, parse_statement

FIXTURES = Path(__file__).parent / "fixtures"
CASES = [
    ("<p>No links here.</p>", False),
    (
        '<p><a href="/newsevents/pressreleases/monetary20250129a1.htm">Implementation Note issued January 29, 2025</a></p>',
        True,
    ),
    (
        '<p>See the <a href="/newsevents/pressreleases/monetary20250129a1.htm">Implementation Note</a>.</p>',
        False,
    ),
    ("<p><a>no href</a></p>", False),
]


@pytest.mark.parametrize(
    "html, expected",
    CASES,
    ids=["no_links", "only_link", "senece_plus_link", "no_href"],
)
def test_is_implementation_note(html, expected):
    p = BeautifulSoup(html, "html.parser").p
    assert is_implementation_note(p) == expected, html


def test_parse_statement():
    # Arrange
    html = (FIXTURES / "monetary20250129a.htm").read_text(encoding="utf-8-sig")
    url = (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250129a.htm"
    )

    # Act
    doc = parse_statement(html, date(2025, 1, 29), url)
    text = doc.sections[0].text

    # Assert: the document
    assert doc.doc_id == "statement-2025-01-29"
    assert doc.doc_type == "statement"
    assert len(doc.sections) == 1
    assert doc.sections[0].key == "statement"
    assert doc.sections[0].heading == "Federal Reserve issues FOMC statement"

    # Assert: kept what's real
    assert text.startswith("Recent indicators suggest")
    assert "Voting for" in text

    # Assert: dropped the boilerplate
    assert "For media inquiries" not in text
    assert "Implementation Note" not in text
