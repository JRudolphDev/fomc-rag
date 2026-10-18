"""Data models for the pipeline. Starts with Meeting: a meeting date plus its statement and minutes URLs."""

from datetime import date

from pydantic import BaseModel


class Meeting(BaseModel):
    meeting_date: date
    statement_url: str
    minutes_url: str | None
