"""Split parsed Documents into Chunks: one per statement, and packed paragraphs within each indexed minutes section."""

import logging

from fomc_rag.models import Chunk, Document

logger = logging.getLogger(__name__)

TARGET_CHARS = 2000  # ~500 tokens at ~4 chars per token
WARN_CHARS = 4000  # ~1,000 tokens

NOT_INDEXED = {
    "preamble",
    "attendance",
    "annual_organizational_matters",
    "organizational_matters",
    "selection_of_committee_officer",
    "notation_vote",
    "notation_votes",
}


def pack_paragraphs(paragraphs: list[str], target_chars: int) -> list[str]:
    """Join consecutive paragraphs with blank lines into chunks of at most target_chars; a paragraph over the target becomes its own chunk."""
    chunks: list[str] = []
    current: list[str] = []
    for p in paragraphs:
        candidate = "\n\n".join(current + [p])
        if current and len(candidate) > target_chars:
            chunks.append("\n\n".join(current))
            current = [p]
        else:
            current.append(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_document(doc: Document, target_chars: int = TARGET_CHARS) -> list[Chunk]:
    """Turn one Document into Chunks numbered across the document, skipping NOT_INDEXED sections: a statement stays whole, minutes sections are packed by paragraph up to target_chars."""
    chunks: list[Chunk] = []
    for section in doc.sections:
        if section.key in NOT_INDEXED:
            continue
        if doc.doc_type == "statement":
            texts = [section.text]
        else:
            texts = pack_paragraphs(section.text.split("\n\n"), target_chars)
        for text in texts:
            if doc.doc_type == "minutes" and len(text) > WARN_CHARS:
                logger.warning(
                    "Oversized chunk in %s, %s: %d chars",
                    doc.doc_id,
                    section.key,
                    len(text),
                )
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}-{len(chunks):03d}",
                    doc_id=doc.doc_id,
                    doc_type=doc.doc_type,
                    meeting_date=doc.meeting_date,
                    section=section.key,
                    heading=section.heading,
                    url=doc.url,
                    text=text,
                )
            )
    return chunks


def context_prefix(chunk: Chunk) -> str:
    """Return the label added to a chunk's embedded text only: document type and spelled-out date, plus the section heading for minutes."""
    d = chunk.meeting_date
    if chunk.doc_type == "statement":
        return f"FOMC statement, {d:%B} {d.day}, {d.year}"
    return f"FOMC minutes, {d:%B} {d.day}, {d.year}, {chunk.heading}"
