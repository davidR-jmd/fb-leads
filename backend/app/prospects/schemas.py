"""Prospect Finder API schemas (request/response models)."""

from enum import Enum
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class SearchMode(str, Enum):
    """Search mode for prospect finding."""
    MANUAL = "manual"
    EXCEL_IMPORT = "excel_import"


class SearchStatus(str, Enum):
    """Status of a search job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LegalForm(str, Enum):
    """French company legal forms."""
    SAS = "SAS"
    SARL = "SARL"
    SA = "SA"
    EURL = "EURL"
    SCI = "SCI"
    OTHER = "OTHER"


# =============================================================================
# Nested Models
# =============================================================================

class CompanyAddress(BaseModel):
    """Company address structure."""
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None


class CompanyData(BaseModel):
    """Company information from Pappers."""
    name: str
    siren: str | None = None
    siret: str | None = None
    revenue: int | None = None  # Chiffre d'affaires in euros
    employees: int | None = None  # Effectif
    employees_range: str | None = None  # e.g., "50 a 99 salaries"
    address: CompanyAddress | None = None
    naf_code: str | None = None  # Code APE/NAF
    naf_label: str | None = None  # Libelle du code NAF
    legal_form: str | None = None  # SAS, SARL, SA, etc.
    creation_date: str | None = None


class ContactData(BaseModel):
    """Contact information from LinkedIn."""
    name: str | None = None
    title: str | None = None
    linkedin_url: str | None = None


class SearchFilters(BaseModel):
    """Optional filters for manual search."""
    company_name: str | None = None
    departements: list[str] | None = None  # e.g., ["69", "75"]
    size_min: int | None = None
    size_max: int | None = None
    revenue_min: int | None = None
    revenue_max: int | None = None
    industry_naf: str | None = None  # NAF/APE code
    is_public: bool | None = None  # True = SA, False = SAS/SARL


class SearchProgress(BaseModel):
    """Progress of a search job."""
    total_companies: int = 0
    processed: int = 0
    found: int = 0
    errors: int = 0


class ColumnMapping(BaseModel):
    """Excel column mapping."""
    company_name: str | None = None
    siren: str | None = None
    siret: str | None = None
    location: str | None = None


# =============================================================================
# Request Models
# =============================================================================

class ProspectSearchRequest(BaseModel):
    """Request to start a prospect search (manual mode)."""

    # Required
    job_function: str = Field(..., min_length=1, description="Job function to search (e.g., 'Directeur Commercial')")

    # Optional filters
    filters: SearchFilters | None = None


class ProspectImportRequest(BaseModel):
    """Request metadata for Excel import (file sent separately)."""

    # Required
    job_function: str = Field(..., min_length=1, description="Job function to search")

    # Optional
    column_mapping: ColumnMapping | None = None  # Auto-detected if not provided


class CompanyLookupRequest(BaseModel):
    """Request to lookup a single company."""
    query: str = Field(..., min_length=1)
    by: str = Field(default="name", pattern="^(name|siren)$")


# =============================================================================
# Response Models
# =============================================================================

class ProspectResult(BaseModel):
    """A single prospect result."""
    company: CompanyData
    contact: ContactData | None = None
    searched_function: str
    linkedin_found: bool = False
    source: str = "pappers"  # pappers, excel, google


class ProspectSearchResponse(BaseModel):
    """Response after starting a search."""
    job_id: str
    status: SearchStatus
    estimated_companies: int = 0
    message: str | None = None


class ProspectSearchResultsResponse(BaseModel):
    """Response with search results."""
    job_id: str
    status: SearchStatus
    progress: SearchProgress
    results: list[ProspectResult]


class CompanyLookupResponse(BaseModel):
    """Response for company lookup."""
    companies: list[CompanyData]


class ExcelImportResponse(BaseModel):
    """Response after Excel import."""
    job_id: str
    status: SearchStatus
    companies_detected: int
    column_mapping: ColumnMapping


class RateLimitStatus(BaseModel):
    """Status of rate limits for an API."""
    requests_today: int
    limit_today: int
    requests_remaining: int
    cooldown_until: str | None = None


class RateLimitsResponse(BaseModel):
    """Response with all rate limit statuses."""
    pappers: RateLimitStatus | None = None
    google_search: RateLimitStatus | None = None
    sirene: RateLimitStatus | None = None


# =============================================================================
# Simple Search (V1 - Simplest workflow)
# =============================================================================

class SimpleSearchRequest(BaseModel):
    """Simplest search request: function + company name."""

    job_function: str = Field(..., min_length=1, description="Job function (e.g., 'Directeur Commercial')")
    company_name: str = Field(..., min_length=1, description="Company name (e.g., 'Carrefour')")


class SimpleSearchResponse(BaseModel):
    """Response for simple search."""
    company: CompanyData
    contacts: list[ContactData] = []  # Multiple LinkedIn profiles
    searched_function: str
    linkedin_found: bool = False
    profiles_count: int = 0  # Number of profiles found
