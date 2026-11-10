import logging
from datetime import date

import pytest

from fomc_rag.chunk import WARN_CHARS, chunk_document, pack_paragraphs
from fomc_rag.models import Document, Section

TARGET = 10
PACK_CASES = [
    ([], []),
    (["aaaa"], ["aaaa"]),
    (["aaaa", "bbbb"], ["aaaa\n\nbbbb"]),
    (["aaaa", "bbbbb"], ["aaaa", "bbbbb"]),
    (["aa", "bb", "cc"], ["aa\n\nbb\n\ncc"]),
    (["aaaaaaaaaaaa", "bb"], ["aaaaaaaaaaaa", "bb"]),
    (["aa", "bbbbbbbbbbbb", "cc"], ["aa", "bbbbbbbbbbbb", "cc"]),
]


@pytest.mark.parametrize(
    "paragraphs, expected",
    PACK_CASES,
    ids=[
        "empty",
        "single",
        "exactly_target",
        "one_over",
        "three_fit",
        "oversized_first",
        "oversized_middle",
    ],
)
def test_pack_paragraphs(paragraphs, expected):
    assert pack_paragraphs(paragraphs, TARGET) == expected


def make_doc(doc_type, sections):
    return Document(
        doc_id=f"{doc_type}-2025-01-29",
        doc_type=doc_type,
        meeting_date=date(2025, 1, 29),
        url="https://example.com",
        sections=tuple(Section(key=k, heading=k, text=t) for k, t in sections),
    )


def test_minutes_skips_not_indexed_and_numbers_without_gaps():
    long_para = "a" * 1500
    doc = make_doc(
        "minutes",
        [
            ("preamble", "date line"),
            ("policy_action", f"{long_para}\n\n{long_para}\n\n{long_para}"),
            ("staff_outlook", f"{long_para}\n\n{long_para}"),
        ],
    )
    ids = [c.chunk_id[-3:] for c in chunk_document(doc)]
    assert ids == [
        "000",
        "001",
        "002",
        "003",
        "004",
    ]


def test_statement_stays_whole_and_does_not_warn(caplog):
    text = "\n\n".join(["a" * 2500, "b" * 2500])  # over WARN_CHARS
    chunks = chunk_document(make_doc("statement", [("statement", text)]))
    assert len(chunks) == 1
    assert not caplog.records


def test_oversized_minutes_paragraph_warns(caplog):
    doc = make_doc("minutes", [("policy_action", "a" * (WARN_CHARS + 1))])
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert any(r.levelno >= logging.WARNING for r in caplog.records)
