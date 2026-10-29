"""Parse statement and minutes pages into Documents: keep the article text, split minutes into sections, drop boilerplate."""

import logging
import re
from datetime import date

from bs4 import BeautifulSoup, Tag

from fomc_rag.models import Document, Section

logger = logging.getLogger(__name__)

MONTHS_ALTERNATION = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_LINE_PATTERN = re.compile(rf"(?:{MONTHS_ALTERNATION}) \d{{1,2}}(?!\d)")
CORE_SECTIONS = {
    "developments in financial markets and open market operations": "financial_markets",
    "staff review of the economic situation": "economic_situation",
    "staff review of the financial situation": "financial_situation",
    "staff economic outlook": "staff_outlook",
    "participants' views on current conditions and the economic outlook": "participants_views",
    "committee policy action": "policy_action",  # 2019 spelling
    "committee policy actions": "policy_action",  # 2025 spelling
}


def is_date_line(text: str) -> bool:
    """True if the text starts with a meeting date."""
    return DATE_LINE_PATTERN.match(text) is not None


def slugify(text: str) -> str:
    """Lowercase the text and join its words with single underscores, e.g. 'Notation Vote' -> 'notation_vote'."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def classify_heading(heading: str) -> str:
    """Return the core section key for a minutes heading, or a slug of the heading if it is not core."""
    return CORE_SECTIONS.get(heading.lower(), slugify(heading))


def is_implementation_note(p: Tag) -> bool:
    """True if the paragraph is only a link to an Implementation Note."""
    links = p.find_all("a")
    return (
        len(links) == 1
        and links[0].get("href", "").endswith("a1.htm")
        and links[0].get_text(" ", strip=True) == p.get_text(" ", strip=True)
    )


def parse_statement(html: str, meeting_date: date, url: str) -> Document:
    """Parse a statement page into a one-section Document, minus the Implementation Note and media lines."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("div", id="article")
    if article is None:
        raise ValueError(f"No div#article in {url}")
    title = article.find("h3", class_="title")
    if title is None:
        raise ValueError(f"No <h3 class='title'> in div#article of {url}")
    heading = title.get_text(" ", strip=True)

    paragraphs: list[str] = []
    for p in article.find_all("p"):
        if p.get("class") or not p.get_text(strip=True):
            continue  # header lines and empty <p>
        text = p.get_text(" ", strip=True)
        if is_implementation_note(p):
            logger.debug("Dropped Implementation Note in %s: %s", url, text)
            continue
        if text.startswith("For media inquiries"):
            logger.debug("Dropped media contact line in %s: %s", url, text)
            continue
        paragraphs.append(text)

    if not paragraphs:
        raise ValueError(f"No statement paragraphs found in {url}")

    section = Section(key="statement", heading=heading, text="\n\n".join(paragraphs))
    return Document(
        doc_id=f"statement-{meeting_date.isoformat()}",
        doc_type="statement",
        meeting_date=meeting_date,
        url=url,
        sections=(section,),
    )
