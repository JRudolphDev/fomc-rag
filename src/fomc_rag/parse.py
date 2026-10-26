import logging
from datetime import date

from bs4 import BeautifulSoup, Tag

from fomc_rag.models import Document, Section

logger = logging.getLogger(__name__)


def is_implementation_note(p: Tag) -> bool:
    """True if the paragraph is only a link to an Implementation Note."""
    links = p.find_all("a")
    return (
        len(links) == 1
        and links[0].get("href", "").endswith("a1.htm")
        and links[0].get_text(" ", strip=True) == p.get_text(" ", strip=True)
    )


def parse_statement(html: str, meeting_date: date, url: str) -> Document:
    """One line."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("div", id="article")
    if article is None:
        raise ValueError(f"No div#article in {url}")
    title = article.find("h3", class_="title")
    if title is None:
        raise ValueError(f"No <h3 class='title'> in div#article of {url}")

    paragraphs: list[str] = []
    for p in article.find_all("p"):
        if p.get("class") or not p.get_text(strip=True):
            continue  # header lines and empty <p>
        text = p.get_text(" ", strip=True)
        if is_implementation_note(p):
            logger.debug(
                logger.debug("Dropped Implementation Note in %s: %s", url, text)
            )
            continue
        if text.startswith(""):  # TODO
            logger.debug("")  # TODO
            continue
        paragraphs.append(text)

    if not paragraphs:
        raise ValueError(f"No statement paragraphs found in {url}")

    section = Section(key="statement", heading=title, text="\n\n".join(paragraphs))
    return Document(
        doc_id=,  # TODO
        doc_type="statement",
        meeting_date=meeting_date,
        url=url,
        sections=(section,),
    )
