"""LinkedIn search models for database storage."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class SearchResultDocument(BaseModel):
    """A single search result stored in database."""

    name: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    profile_url: str | None = None
    searched_company: str  # The company name used in search
    searched_keywords: str = ""  # Keywords used in search


class SearchSessionDocument(BaseModel):
    """A search session containing multiple results."""

    id: str = Field(alias="_id")
    user_id: str
    companies: list[str]  # Original company list
    keywords: str = ""
    status: str = "in_progress"  # in_progress, completed, failed
    results: list[SearchResultDocument] = []
    companies_searched: int = 0
    total_companies: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
