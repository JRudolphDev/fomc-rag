"""Data models for the pipeline: meetings from discovery, documents and sections from parsing."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Meeting(BaseModel):
    model_config = ConfigDict(frozen=True)

    meeting_date: date
    statement_url: str
    minutes_url: str | None


class Section(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    heading: str
    text: str


class Document(BaseModel):
    model_config = ConfigDict(frozen=True)

    doc_id: str
    doc_type: Literal["statement", "minutes"]
    meeting_date: date
    url: str
    sections: tuple[Section]
