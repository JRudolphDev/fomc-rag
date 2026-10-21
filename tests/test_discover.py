from datetime import date
from pathlib import Path

import pytest

from fomc_rag.discover import extract_links, historical_url, url_date

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_links_2020():
    # Arrange: load the input
    html = (FIXTURES / "fomchistorical2020.htm").read_text(encoding="utf-8-sig")

    # Act: call the function once
    statements, minutes = extract_links(html)

    # Assert: check the facts
    assert len(statements) == 12
    assert len(minutes) == 8
    # Mar 15 minutes also contain the Mar 3 emergency meeting's minutes.
    assert (
        "https://www.federalreserve.gov/monetarypolicy/fomcminutes20200315.htm"
        in minutes
    )

    assert (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm"
        in statements
    )
    assert all(url.startswith("https://") for url in statements | minutes)
    assert (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200331a.htm"
        in statements
    )


def test_url_date():
    assert url_date(
        "https://www.federalreserve.gov/monetarypolicy/fomcminutes20200129.htm"
    ) == date(2020, 1, 29)
    assert url_date(
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200331a.htm"
    ) == date(2020, 3, 31)
    with pytest.raises(ValueError, match="no date in URL"):
        url_date("https://example.com/nope.htm")
    with pytest.raises(ValueError):
        url_date(
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20201399a.htm"
        )


def test_historical_url():
    assert (
        historical_url(2020)
        == "https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm"
    )
