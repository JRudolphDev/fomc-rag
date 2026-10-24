"""Data models for the pipeline. Starts with Meeting: a meeting date plus its statement and minutes URLs."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class Meeting(BaseModel):
    model_config = ConfigDict(frozen=True)

    meeting_date: date
    statement_url: str
    minutes_url: str | None
