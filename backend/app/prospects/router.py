"""Prospect Finder API router."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.database import get_database
from app.prospects.service import ProspectService, get_prospect_service
from app.prospects.schemas import (
    SimpleSearchRequest,
    SimpleSearchResponse,
    ProspectSearchRequest,
    ProspectSearchResponse,
    ProspectSearchResultsResponse,
    CompanyLookupRequest,
    CompanyLookupResponse,
    SearchStatus,
    SearchProgress,
    ProspectResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prospects", tags=["prospects"])


# =============================================================================
# Dependencies
# =============================================================================

async def get_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> ProspectService:
    """Get prospect service instance."""
    return get_prospect_service(db)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/simple-search", response_model=SimpleSearchResponse)
async def simple_search(
    request: SimpleSearchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ProspectService, Depends(get_service)],
) -> SimpleSearchResponse:
    """
    Simple search: Find a contact by job function and company name.

    This is the simplest workflow:
    1. Look up company in Pappers (French company database)
    2. Search for LinkedIn profile via Google
    3. Return company info + LinkedIn URL

    The LinkedIn URL can then be used with the Lusha Chrome plugin
    to get phone/email.

    **Required:**
    - `job_function`: Job title to search (e.g., "Directeur Commercial")
    - `company_name`: Company name (e.g., "Carrefour")

    **Returns:**
    - Company data (name, SIREN, revenue, employees, etc.)
    - Contact data with LinkedIn URL (if found)
    """
    try:
        return await service.simple_search(request)
    except Exception as e:
        logger.error(f"Simple search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("/search", response_model=ProspectSearchResponse)
async def search_prospects(
    request: ProspectSearchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ProspectService, Depends(get_service)],
) -> ProspectSearchResponse:
    """
    Search for prospects with filters.

    Start a search job that finds contacts matching the criteria.

    **Required:**
    - `job_function`: Job title to search (e.g., "DSI", "DRH")

    **Optional filters:**
    - `company_name`: Specific company to search
    - `departements`: List of French department codes (e.g., ["69", "75"])
    - `size_min`, `size_max`: Employee count range
    - `revenue_min`, `revenue_max`: Revenue range in euros
    - `industry_naf`: NAF/APE industry code
    - `is_public`: True for public companies (SA), False for private

    **Returns:**
    - `job_id`: ID to retrieve results
    - `status`: Current status (pending, processing, completed, failed)
    """
    try:
        user_id = str(current_user.get("_id", current_user.get("id", "")))
        return await service.search_with_filters(user_id, request)
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/search/{job_id}", response_model=ProspectSearchResultsResponse)
async def get_search_results(
    job_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[ProspectService, Depends(get_service)],
) -> ProspectSearchResultsResponse:
    """
    Get results for a search job.

    **Returns:**
    - `status`: Current job status
    - `progress`: Number of companies processed
    - `results`: List of prospects found
    """
    job = await service.get_job_results(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search job not found",
        )

    # Convert raw results to ProspectResult
    results = []
    for r in job.get("results", []):
        from app.prospects.schemas import CompanyData, ContactData, CompanyAddress

        # Build company address
        address = None
        if r.get("company_address_city"):
            address = CompanyAddress(
                street=r.get("company_address_street"),
                postal_code=r.get("company_address_postal_code"),
                city=r.get("company_address_city"),
            )

        company = CompanyData(
            name=r.get("company_name", ""),
            siren=r.get("company_siren"),
            siret=r.get("company_siret"),
            revenue=r.get("company_revenue"),
            employees=r.get("company_employees"),
            employees_range=r.get("company_employees_range"),
            address=address,
            naf_code=r.get("company_naf_code"),
            naf_label=r.get("company_naf_label"),
            legal_form=r.get("company_legal_form"),
            creation_date=r.get("company_creation_date"),
        )

        contact = None
        if r.get("contact_linkedin_url") or r.get("contact_name"):
            contact = ContactData(
                name=r.get("contact_name"),
                title=r.get("contact_title"),
                linkedin_url=r.get("contact_linkedin_url"),
            )

        results.append(ProspectResult(
            company=company,
            contact=contact,
            searched_function=r.get("searched_function", ""),
            linkedin_found=r.get("linkedin_found", False),
            source=r.get("source", "pappers"),
        ))

    progress_data = job.get("progress", {})
    progress = SearchProgress(
        total_companies=progress_data.get("total_companies", 0),
        processed=progress_data.get("processed", 0),
        found=progress_data.get("found", 0),
        errors=progress_data.get("errors", 0),
    )

    return ProspectSearchResultsResponse(
        job_id=job_id,
        status=SearchStatus(job.get("status", "pending")),
        progress=progress,
        results=results,
    )


@router.post("/company/lookup", response_model=CompanyLookupResponse)
async def lookup_company(
    request: CompanyLookupRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CompanyLookupResponse:
    """
    Look up a company by name or SIREN.

    Useful for autocomplete or validation.

    **Parameters:**
    - `query`: Company name or SIREN to search
    - `by`: Search type - "name" or "siren"
    """
    from app.prospects.clients.pappers import get_pappers_client

    pappers = get_pappers_client()

    try:
        if request.by == "siren":
            company = await pappers.get_by_siren(request.query)
            companies = [company] if company else []
        else:
            company = await pappers.search_by_name(request.query)
            companies = [company] if company else []

        return CompanyLookupResponse(companies=companies)

    except Exception as e:
        logger.error(f"Company lookup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lookup failed: {str(e)}",
        )
