from pathlib import Path

from fomc_rag.discover import extract_links

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_links_2020():
    # Arrange: load the input
    html = (FIXTURES / "fomchistorical2020.htm").read_text(encoding="utf-8")

    # Act: call the function once
    statements, minutes = extract_links(html)

    # Assert: check the facts
    assert len(statements) == 12
    # your asserts here
