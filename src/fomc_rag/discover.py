"""Find FOMC meetings from year pages: extract statement and minutes links, pair them by date, keep only real statements."""

import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from fomc_rag.fetch import fetch_cached
from fomc_rag.models import Meeting

BASE_URL = "https://www.federalreserve.gov"
STATEMENT_PATTERN = re.compile(r"/newsevents/pressreleases/monetary(\d{8})a\.htm")
MINUTES_PATTERN = re.compile(r"/monetarypolicy/fomcminutes(\d{8})\.htm")
CALENDAR_URL = urljoin(BASE_URL, "/monetarypolicy/fomccalendars.htm")


def extract_links(html: str) -> tuple[set[str], set[str]]:
    """Return statement and minutes URLs found in a year page."""
    soup = BeautifulSoup(html, "html.parser")
    statements: set[str] = set()
    minutes: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        if STATEMENT_PATTERN.fullmatch(href):
            statements.add(urljoin(BASE_URL, href))

        elif MINUTES_PATTERN.fullmatch(href):
            minutes.add(urljoin(BASE_URL, href))

    return statements, minutes


def url_date(url: str) -> date:
    """Return the meeting date encoded in a statement or minutes URL."""
    path = urlparse(url).path
    m = STATEMENT_PATTERN.fullmatch(path) or MINUTES_PATTERN.fullmatch(path)

    if m is None:
        raise ValueError(f"no date in URL: {url}")

    digits = m.group(1)
    return datetime.strptime(digits, "%Y%m%d").date()


def historical_url(year: int) -> str:
    """Return the URL of the FOMC historical page for a year."""
    return urljoin(BASE_URL, f"/monetarypolicy/fomchistorical{year}.htm")


def fetch_links(
    url: str, cache_dir: Path, refresh: bool = False
) -> tuple[set[str], set[str]]:
    """Fetch a year page and return its statement and minutes URLs."""
    html = fetch_cached(url, cache_dir, refresh)
    statements, minutes = extract_links(html)

    if not statements and not minutes:
        raise ValueError(
            f"No statement or minutes links found on {url}. "
            "The page layout or URL patterns may have changed."
        )

    return statements, minutes


def pair_meetings(statements: set[str], meetings: set[str]) -> list[Meeting]:
    raise NotImplementedError


def discover_meetings(start_year: int, cache_dir: Path) -> list[Meeting]:
    """Return meetings from start_year onward, paired and title-checked."""
    statements, minutes = fetch_links(CALENDAR_URL, cache_dir, refresh=True)
    boundary_year = min(url_date(u).year for u in statements | minutes)

    for year in range(start_year, boundary_year):
        year_url = historical_url(year)
        year_statements, year_minutes = fetch_links(year_url, cache_dir, refresh=False)

        statements |= year_statements
        minutes |= year_minutes

    statements = {u for u in statements if url_date(u).year >= start_year}
    minutes = {u for u in minutes if url_date(u).year >= start_year}

    print(statements, minutes)
    print(sorted({url_date(u).year for u in statements | minutes}))


if __name__ == "__main__":
    discover_meetings(start_year=2023, cache_dir=Path("data/raw"))
