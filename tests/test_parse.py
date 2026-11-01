from datetime import date
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from fomc_rag.parse import (
    classify_heading,
    heading_candidate,
    is_date_line,
    is_footnote,
    is_implementation_note,
    parse_minutes,
    parse_statement,
    reject_reason,
)

FIXTURES = Path(__file__).parent / "fixtures"
IMPLEMENTATION_NOTE_CASES = [
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
DATE_LINE_CASES = [
    ("January 29-30, 2019", True),
    ("January 28\u201329, 2025", True),  # en dash
    ("March 15, 2020", True),
    ("March 2020 Actions", False),
    ("Developments in Financial Markets and Open Market Operations", False),
]
CLASSIFY_CASES = [
    ("Committee Policy Action", "policy_action"),
    ("Committee Policy Actions", "policy_action"),
    ("STAFF ECONOMIC OUTLOOK", "staff_outlook"),
    ("Annual Organizational Matters", "annual_organizational_matters"),
    (
        "Review of Monetary Policy Strategy, Tools, and Communications",
        "review_of_monetary_policy_strategy_tools_and_communications",
    ),
]
HEADING_CANDIDATE_CASES = [
    # heading after a leading <br>, body text in the same <p>
    (
        "<p><br /><strong>Staff Economic Outlook</strong><br />The staff projection...</p>",
        "Staff Economic Outlook",
    ),
    # bold word mid-sentence, not a heading
    ("<p>The Committee <strong>agreed</strong> to...</p>", None),
    # empty <strong> mid-sentence (real, 2019 fixture line 1862)
    ("<p>the labor market.<strong> </strong>These factors may change</p>", None),
]
REJECT_REASON_CASES = [
    ("<p><strong>Voting for this action:</strong></p>", "vote label"),
    ("<p><strong>January 28\u201329, 2025</strong><br/></p>", "date line"),
    (
        '<p style="text-align:center"><strong>Joshua Gallin</strong><br/>Secretary</p>',
        "signature",
    ),
    ("<p><strong>Staff Economic Outlook</strong><br/>The staff...</p>", None),
]
FOOTNOTE_CASES = [
    (
        '<p><a name="fn1"></a>1. The Federal Open Market Committee is referenced as the "FOMC". <a href="#f1">Return to text</a></p>',
        True,
    ),
    (
        '<p><a name="fn3"></a>3. The SLOOS results reported are based on... <a href="#f3">Return to text</a></p>',
        True,
    ),
    (
        '<p><strong>Annual Organizational Matters</strong><a href="#fn4" title="footnote 4"></a><a name="f4"></a><br/>In the agenda...</p>',
        False,
    ),
    ("<p>Participants agreed that...</p>", False),
]
MINUTES_CASES = [
    (
        "fomcminutes20190130.htm",
        date(2019, 1, 30),
        "minutes-2019-01-30",
        (
            "preamble",
            "annual_organizational_matters",
            "financial_markets",
            "long_run_monetary_policy_implementation_frameworks",
            "economic_situation",
            "financial_situation",
            "staff_outlook",
            "participants_views",
            "policy_action",
            "notation_vote",
        ),
        "Cavallo, 2",
    ),
    (
        "fomcminutes20250129.htm",
        date(2025, 1, 29),
        "minutes-2025-01-29",
        (
            "preamble",
            "annual_organizational_matters",
            "review_of_monetary_policy_strategy_tools_and_communications",
            "financial_markets",
            "economic_situation",
            "financial_situation",
            "staff_outlook",
            "participants_views",
            "policy_action",
            "notation_vote",
            "attendance",
        ),
        "Altig, 4",
    ),
]


@pytest.mark.parametrize(
    "html, expected",
    IMPLEMENTATION_NOTE_CASES,
    ids=["no_links", "only_link", "sentence_plus_link", "no_href"],
)
def test_is_implementation_note(html, expected):
    p = BeautifulSoup(html, "html.parser").p
    assert is_implementation_note(p) == expected, html


@pytest.mark.parametrize(
    "text, expected",
    DATE_LINE_CASES,
    ids=["hyphen", "en_dash", "single_day", "year_not_day", "heading"],
)
def test_is_date_line(text, expected):
    assert is_date_line(text) == expected, text


@pytest.mark.parametrize(
    "heading, expected",
    CLASSIFY_CASES,
    ids=[
        "action_2019",
        "actions_2025",
        "case_insensitive",
        "routine_slug",
        "punctuation_slug",
    ],
)
def test_classify_heading(heading, expected):
    assert classify_heading(heading) == expected, heading


@pytest.mark.parametrize(
    "html, expected",
    HEADING_CANDIDATE_CASES,
    ids=["leading_br", "inline_bold", "empty"],
)
def test_heading_candidate(html, expected):
    p = BeautifulSoup(html, "html.parser").p
    result = heading_candidate(p)
    assert (
        result.get_text(" ", strip=True) if result is not None else result
    ) == expected, html


@pytest.mark.parametrize(
    "html, expected",
    REJECT_REASON_CASES,
    ids=["vote_label", "date_line", "signature", "valid_heading"],
)
def test_reject_reason(html, expected):
    p = BeautifulSoup(html, "html.parser").p
    text = p.strong.get_text(" ", strip=True)
    assert reject_reason(p, text) == expected, html


@pytest.mark.parametrize(
    "html, expected",
    FOOTNOTE_CASES,
    ids=["footnote", "footnote_not_first", "marker_anchor", "plain"],
)
def test_is_footnote(html, expected):
    p = BeautifulSoup(html, "html.parser").p
    assert is_footnote(p) == expected, html


@pytest.mark.parametrize(
    "filename, meeting_date, expected_id, expected_keys, leaked_marker",
    MINUTES_CASES,
    ids=["2019", "2025"],
)
def test_parse_minutes(
    filename, meeting_date, expected_id, expected_keys, leaked_marker
):
    html = (FIXTURES / filename).read_text(encoding="utf-8-sig")
    url = f"https://www.federalreserve.gov/monetarypolicy/{filename}"
    doc = parse_minutes(html, meeting_date, url)
    keys = tuple(s.key for s in doc.sections)
    headings = [s.heading for s in doc.sections]
    all_text = "\n\n".join(s.text for s in doc.sections)

    assert doc.doc_id == expected_id
    assert keys == expected_keys
    assert (
        doc.sections[0].heading == "Minutes of the Federal Open Market Committee"
    )  # preamble uses the page <h3>
    assert "Annual Organizational Matters" in headings  # footnote digit stripped
    assert "Return to text" not in all_text  # footnotes dropped
    assert not any(h.endswith(":") for h in headings)  # vote labels rejected
    assert leaked_marker not in all_text  # footnote digits stripped from body text


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
