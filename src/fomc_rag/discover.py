"""Find FOMC meetings from year pages: extract statement and minutes links, pair them by date, keep only real statements."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE_URL = "https://www.federalreserve.gov"
STATEMENT_PATTERN = re.compile(r"/newsevents/pressreleases/monetary(\d{8})a\.htm")
MINUTES_PATTERN = re.compile(r"/monetarypolicy/fomcminutes(\d{8})\.htm")


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
