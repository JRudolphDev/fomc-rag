"""Parse statement and minutes pages into Documents: keep the article text, split minutes into sections, drop boilerplate."""

import logging
import re
from datetime import date

from bs4 import BeautifulSoup, NavigableString, Tag

from fomc_rag.models import Document, Section

logger = logging.getLogger(__name__)

MONTHS_ALTERNATION = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_LINE_PATTERN = re.compile(rf"(?:{MONTHS_ALTERNATION}) \d{{1,2}}(?!\d)")
CORE_SECTIONS = {
    "developments in financial markets and open market operations": "financial_markets",
    "discussion of financial markets and open market operations": "financial_markets",
    "financial developments and open market operations": "financial_markets",
    "staff review of the economic situation": "economic_situation",
    "staff review of the financial situation": "financial_situation",
    "staff economic outlook": "staff_outlook",
    "participants' views on current conditions and the economic outlook": "participants_views",
    "participants' views on current economic conditions and the economic outlook": "participants_views",
    "committee policy action": "policy_action",  # 2019 spelling
    "committee policy actions": "policy_action",  # 2025 spelling
}
KNOWN_NON_CORE = {
    # routine and meeting logistics
    "annual_organizational_matters",
    "organizational_matters",
    "selection_of_committee_officer",
    "notation_vote",
    "notation_votes",
    "attendance",
    "opening_remarks",
    "videoconference_meeting_of_march_2",  # Mar 3 2020 minutes inside Mar 15
    "videoconference_meeting_of_october_4_2019",
    # policy framework and communications
    "long_run_monetary_policy_implementation_frameworks",
    "review_of_monetary_policy_strategy_tools_and_communication_practices",  # 2019-20
    "review_of_monetary_policy_strategy_tools_and_communications",  # 2025
    "update_from_subcommittee_on_communications",
    "discussion_of_forward_guidance_asset_purchases_and_yield_curve_caps_or_targets",
    "discussion_on_recommended_changes_to_the_summary_of_economic_projections",
    "action_to_adopt_changes_to_the_committee_s_rules_regarding_availability_of_information",
    "committee_ethics_discussion",
    # balance sheet and asset purchases
    "balance_sheet_normalization",
    "reinvestment_plans",
    "discussion_on_asset_purchases",
    "discussion_of_asset_purchases",
    "discussion_of_policy_normalization_considerations",
    "principles_for_reducing_the_size_of_the_balance_sheet",
    "plans_for_reducing_the_size_of_the_balance_sheet",
    "considerations_for_slowing_the_pace_of_balance_sheet_reduction",
    "special_topic_balance_sheet_issues",
    # money markets and repo
    "participants_discussion_of_recent_money_market_developments",
    "review_of_options_for_repo_operations_to_support_control_of_the_federal_funds_rate",
    "standing_repurchase_facility",
    "discussion_of_repurchase_agreement_arrangements",
    "establishment_of_standing_repurchase_agreement_facilities",
    "standing_repurchase_agreement_facility_resolution",
    "standing_fima_repurchase_agreement_resolution",
    "special_topic_the_standing_repo_facility",
    # financial stability
    "recent_developments_in_the_banking_sector",
}
VOTE_LABEL_PREFIXES = ("Voting for", "Voting against", "Absent and not voting")


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


def is_footnote(p: Tag) -> bool:
    """True if the paragraph is a page footnote, marked by an <a name="fn..."> anchor."""
    anchor = p.find("a", attrs={"name": True})  # first <a> that has a name attribute
    return anchor is not None and anchor.get("name", "").startswith("fn")


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


def heading_candidate(p: Tag) -> Tag | None:
    """Return the <strong> that starts the paragraph, ignoring whitespace and <br>, or None."""
    for child in p.children:
        if isinstance(child, NavigableString) and not child.strip():
            continue  # whitespace: keep looking
        if child.name == "br":
            continue  # a leading <br>: keep looking
        return child if child.name == "strong" else None
    return None


def reject_reason(p: Tag, text: str) -> str | None:
    """Return why a heading candidate is rejected (vote label, trailing colon, date line, signature), else None."""
    if text.startswith(VOTE_LABEL_PREFIXES):
        return "vote label"
    if text.endswith(":"):
        return "trailing colon"
    if is_date_line(text):
        return "date line"
    if "text-align:center" in p.get("style", ""):
        return "signature"
    return None


def parse_minutes(html: str, meeting_date: date, url: str) -> Document:
    """Parse a minutes page into a Document with one section per heading, plus a preamble."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("div", id="article")
    if article is None:
        raise ValueError(f"No div#article in {url}")
    title = article.find("h3")
    if title is None:
        raise ValueError(f"No <h3> in div#article of {url}")
    for sup in article.find_all("sup"):
        sup.decompose()  # remove footnote markers everywhere, once

    groups: list[tuple[str, str, list[str]]] = []
    key, heading, paragraphs = "preamble", title.get_text(" ", strip=True), []
    rejects = 0
    for p in article.find_all("p"):
        if is_footnote(p):
            logger.debug("Dropped footnote in %s: %s", url, p.get_text(" ", strip=True))
            continue
        strong = heading_candidate(p)
        if strong is not None:
            text = strong.get_text(" ", strip=True)
            reason = reject_reason(p, text)
            if reason is not None:
                logger.debug("Rejected %s in %s: %s", reason, url, text)
                rejects += 1
            else:
                groups.append((key, heading, paragraphs))  # flush the current section
                key, heading, paragraphs = classify_heading(text), text, []
                strong.decompose()  # heading text is read; leave only the body
        body = p.get_text(" ", strip=True)
        if body:
            paragraphs.append(body)
    groups.append((key, heading, paragraphs))  # final flush

    sections = tuple(
        Section(key=k, heading=h, text="\n\n".join(ps)) for k, h, ps in groups if ps
    )
    if not sections:
        raise ValueError(f"No section paragraphs found in {url}")
    core_keys = set(CORE_SECTIONS.values())
    non_core = [
        s.key for s in sections if s.key not in core_keys and s.key != "preamble"
    ]
    for key in non_core:
        if key not in KNOWN_NON_CORE:
            logger.warning("Unknown non-core section in %s: %s", url, key)
    doc_id = f"minutes-{meeting_date.isoformat()}"
    logger.info(
        "Parsed %s: %d sections, %d rejected candidates, non-core: %s",
        doc_id,
        len(sections),
        rejects,
        non_core,
    )
    return Document(
        doc_id=doc_id,
        doc_type="minutes",
        meeting_date=meeting_date,
        url=url,
        sections=sections,
    )
