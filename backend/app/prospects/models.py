"""Prospect Finder MongoDB document models."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.prospects.schemas import (
    SearchMode,
    SearchStatus,
    SearchFilters,
    SearchProgress,
    ColumnMapping,
    CompanyData,
    ContactData,
)


# =============================================================================
# MongoDB Document Models
# =============================================================================

class ProspectResultDocument(BaseModel):
    """A single prospect result stored in database."""

    # Company data (from Pappers or Excel)
    company_name: str
    company_siren: str | None = None
    company_siret: str | None = None
    company_revenue: int | None = None
    company_employees: int | None = None
    company_employees_range: str | None = None
    company_address_street: str | None = None
    company_address_postal_code: str | None = None
    company_address_city: str | None = None
    company_naf_code: str | None = None
    company_naf_label: str | None = None
    company_legal_form: str | None = None
    company_creation_date: str | None = None

    # Contact data (from Google/LinkedIn) - multiple contacts
    contacts: list[dict[str, Any]] = []  # List of {name, title, linkedin_url}

    # Search metadata
    searched_function: str
    linkedin_found: bool = False
    profiles_count: int = 0  # Number of profiles found
    source: str = "pappers"  # pappers, excel, google

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SearchJobDocument(BaseModel):
    """A search job containing configuration and results."""

    id: str = Field(alias="_id")

    # User reference
    user_id: str

    # Search parameters
    job_function: str
    mode: SearchMode = SearchMode.MANUAL

    # Manual search filters (optional)
    filters: SearchFilters | None = None

    # Excel import (optional)
    excel_file_id: str | None = None  # GridFS reference
    column_mapping: ColumnMapping | None = None
    excel_companies: list[str] = []  # Company names from Excel

    # Status and progress
    status: SearchStatus = SearchStatus.PENDING
    progress: SearchProgress = Field(default_factory=SearchProgress)

    # Results
    results: list[ProspectResultDocument] = []

    # Error tracking
    error_message: str | None = None
    failed_companies: list[str] = []

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)


class CompanyCacheDocument(BaseModel):
    """Cached company data from Pappers (TTL: 30 days)."""

    id: str = Field(alias="_id")  # SIREN as ID

    # Company data
    name: str
    siren: str
    siret_siege: str | None = None
    revenue: int | None = None
    employees: int | None = None
    employees_range: str | None = None
    address_street: str | None = None
    address_postal_code: str | None = None
    address_city: str | None = None
    naf_code: str | None = None
    naf_label: str | None = None
    legal_form: str | None = None
    creation_date: str | None = None

    # Dirigeants (directors)
    dirigeants: list[dict[str, Any]] = []

    # Cache metadata
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)


class APIRateLimitDocument(BaseModel):
    """Rate limit state for external APIs."""

    id: str = Field(alias="_id")  # API name: pappers, google_search, sirene

    # Counters
    requests_today: int = 0
    requests_this_hour: int = 0
    requests_this_minute: int = 0

    # Timestamps
    day_started: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hour_started: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    minute_started: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_request: datetime | None = None

    # Cooldown
    cooldown_until: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# Document Factory Functions
# =============================================================================

def create_search_job_document(
    user_id: str,
    job_function: str,
    mode: SearchMode = SearchMode.MANUAL,
    filters: SearchFilters | None = None,
    excel_companies: list[str] | None = None,
    column_mapping: ColumnMapping | None = None,
) -> dict[str, Any]:
    """Create a search job document for MongoDB insertion."""
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": user_id,
        "job_function": job_function,
        "mode": mode.value,
        "status": SearchStatus.PENDING.value,
        "progress": {
            "total_companies": 0,
            "processed": 0,
            "found": 0,
            "errors": 0,
        },
        "results": [],
        "failed_companies": [],
        "created_at": now,
        "updated_at": now,
    }

    if filters:
        doc["filters"] = filters.model_dump(exclude_none=True)

    if excel_companies:
        doc["excel_companies"] = excel_companies
        doc["progress"]["total_companies"] = len(excel_companies)

    if column_mapping:
        doc["column_mapping"] = column_mapping.model_dump(exclude_none=True)

    return doc


def create_prospect_result_document(
    company_data: CompanyData,
    contacts: list[ContactData] | None = None,
    searched_function: str = "",
    source: str = "pappers",
) -> dict[str, Any]:
    """Create a prospect result document with multiple contacts."""
    now = datetime.now(timezone.utc)

    # Convert contacts to list of dicts
    contacts_list = []
    if contacts:
        for contact in contacts:
            contacts_list.append({
                "name": contact.name,
                "title": contact.title,
                "linkedin_url": contact.linkedin_url,
            })

    doc = {
        "company_name": company_data.name,
        "company_siren": company_data.siren,
        "company_siret": company_data.siret,
        "company_revenue": company_data.revenue,
        "company_employees": company_data.employees,
        "company_employees_range": company_data.employees_range,
        "company_naf_code": company_data.naf_code,
        "company_naf_label": company_data.naf_label,
        "company_legal_form": company_data.legal_form,
        "company_creation_date": company_data.creation_date,
        "searched_function": searched_function,
        "contacts": contacts_list,
        "linkedin_found": len(contacts_list) > 0,
        "profiles_count": len(contacts_list),
        "source": source,
        "created_at": now,
    }

    # Add address if present
    if company_data.address:
        doc["company_address_street"] = company_data.address.street
        doc["company_address_postal_code"] = company_data.address.postal_code
        doc["company_address_city"] = company_data.address.city

    return doc


def create_company_cache_document(
    siren: str,
    name: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a company cache document for MongoDB insertion."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)  # 30-day TTL

    doc = {
        "_id": siren,
        "siren": siren,
        "name": name,
        "fetched_at": now,
        "expires_at": expires_at,
    }

    # Add optional fields
    optional_fields = [
        "siret_siege", "revenue", "employees", "employees_range",
        "address_street", "address_postal_code", "address_city",
        "naf_code", "naf_label", "legal_form", "creation_date",
        "dirigeants",
    ]

    for field in optional_fields:
        if field in kwargs and kwargs[field] is not None:
            doc[field] = kwargs[field]

    return doc


def create_rate_limit_document(api_name: str) -> dict[str, Any]:
    """Create a rate limit document for an API."""
    now = datetime.now(timezone.utc)

    return {
        "_id": api_name,
        "requests_today": 0,
        "requests_this_hour": 0,
        "requests_this_minute": 0,
        "day_started": now,
        "hour_started": now,
        "minute_started": now,
        "last_request": None,
        "cooldown_until": None,
    }
