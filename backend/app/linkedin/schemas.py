"""LinkedIn module Pydantic schemas (Single Responsibility)."""

from enum import Enum
from pydantic import BaseModel, EmailStr


class LinkedInStatus(str, Enum):
    """LinkedIn connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    NEED_EMAIL_CODE = "need_email_code"
    NEED_MANUAL_LOGIN = "need_manual_login"
    AWAITING_MANUAL_LOGIN = "awaiting_manual_login"  # Browser open, waiting for user
    CONNECTED = "connected"
    BUSY = "busy"
    ERROR = "error"


class LinkedInAuthMethod(str, Enum):
    """Authentication method used."""

    COOKIE = "cookie"
    CREDENTIALS = "credentials"
    MANUAL = "manual"


class LinkedInConnectRequest(BaseModel):
    """Request to connect LinkedIn account."""

    email: EmailStr
    password: str


class LinkedInVerifyCodeRequest(BaseModel):
    """Request to submit verification code."""

    code: str


class LinkedInCookieConnectRequest(BaseModel):
    """Request to connect using li_at cookie."""

    cookie: str


class LinkedInSearchRequest(BaseModel):
    """Request to search LinkedIn."""

    query: str
    limit: int = 50  # Default 50 results, max 100


class LinkedInCompanySearchRequest(BaseModel):
    """Request to search LinkedIn by company list + keywords."""

    companies: list[str]  # List of company names from Excel
    keywords: str = ""  # Additional search keywords (e.g., "Directeur Marketing")
    limit_per_company: int = 10  # Results per company (default 10)


class LinkedInStatusResponse(BaseModel):
    """Response with LinkedIn connection status."""

    status: LinkedInStatus
    email: str | None = None
    last_connected: str | None = None
    error_message: str | None = None
    auth_method: LinkedInAuthMethod | None = None


class LinkedInConnectResponse(BaseModel):
    """Response after connection attempt."""

    status: LinkedInStatus
    message: str | None = None


class LinkedInContact(BaseModel):
    """A LinkedIn contact from search results."""

    name: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    profile_url: str | None = None
    image_url: str | None = None


class LinkedInSearchResponse(BaseModel):
    """Response with LinkedIn search results."""

    contacts: list[LinkedInContact]
    query: str
    total_found: int


class LinkedInCompanySearchResponse(BaseModel):
    """Response with LinkedIn company search results."""

    contacts: list[LinkedInContact]
    companies_searched: int
    total_found: int
    keywords: str


class SearchSessionResponse(BaseModel):
    """Response when starting a search session."""

    session_id: str
    status: str
    total_companies: int
    message: str


class SearchResultsPageResponse(BaseModel):
    """Paginated search results response."""

    results: list[LinkedInContact]
    total: int
    page: int
    page_size: int
    total_pages: int
    companies_searched: int
    total_companies: int
    status: str


class SearchSessionStatusResponse(BaseModel):
    """Search session status response."""

    session_id: str
    status: str
    companies_searched: int
    total_companies: int
    total_results: int
    keywords: str
    created_at: str
