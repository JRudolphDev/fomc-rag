"""Check the test set: every quote appears in its (doc_id, section) text, and that section is indexed."""

import json
import logging
from pathlib import Path

from fomc_rag.chunk import NOT_INDEXED
from fomc_rag.ingest import ingest

QUESTIONS = Path("eval/questions.jsonl")


def source_problem(source: dict, sections: dict[tuple[str, str], str]) -> str | None:
    """Return why a source fails the check, or None if it passes."""
    if source["section"] in NOT_INDEXED:
        return "section is not indexed"  # retrieval can never return it
    text = sections.get((source["doc_id"], source["section"]))
    if text is None:
        return "no such doc_id and section"
    if source["quote"] not in text:
        return "quote not found"
    return None


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    documents = ingest(2019, Path("data/raw"))
    sections = {(d.doc_id, s.key): s.text for d in documents for s in d.sections}
    records = [
        json.loads(line)
        for line in QUESTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    bad = 0
    for record in records:
        for source in record["sources"]:
            problem = source_problem(source, sections)
            if problem is not None:
                print(
                    f"BAD ({problem}): {record['question']} {source['doc_id']} {source['section']}"
                )
                bad += 1
    print(f"{len(records)} questions, {bad} bad sources")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
