"""LinkedIn API router (Single Responsibility)."""

import asyncio
import json
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.admin.dependencies import get_current_admin_user
from app.database import get_database
from app.linkedin.dependencies import get_linkedin_service, get_encryption_service
from app.linkedin.service import LinkedInService
from app.linkedin.search_repository import SearchResultsRepository
from app.linkedin.models import SearchResultDocument
from app.linkedin.http_client import get_linkedin_http_client
from app.linkedin.schemas import (
    LinkedInConnectRequest,
    LinkedInCookieConnectRequest,
    LinkedInVerifyCodeRequest,
    LinkedInSearchRequest,
    LinkedInCompanySearchRequest,
    LinkedInStatusResponse,
    LinkedInConnectResponse,
    LinkedInSearchResponse,
    LinkedInCompanySearchResponse,
    SearchSessionResponse,
    SearchResultsPageResponse,
    SearchSessionStatusResponse,
    LinkedInContact,
)
from app.linkedin.exceptions import (
    LinkedInBrowserBusyError,
    LinkedInBrowserNotRunningError,
    LinkedInNotConfiguredError,
    LinkedInError,
    LinkedInRateLimitError,
)
from app.linkedin.rate_limiter import get_rate_limiter

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


@router.get("/status", response_model=LinkedInStatusResponse)
async def get_status(
    _: Annotated[dict, Depends(get_current_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInStatusResponse:
    """Get LinkedIn connection status. Requires authentication."""
    return await service.get_status()


@router.post("/connect", response_model=LinkedInConnectResponse)
async def connect(
    request: LinkedInConnectRequest,
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInConnectResponse:
    """
    Connect to LinkedIn with credentials.
    Requires admin role.
    """
    try:
        return await service.connect(request.email, request.password)
    except LinkedInBrowserBusyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/connect-cookie", response_model=LinkedInConnectResponse)
async def connect_with_cookie(
    request: LinkedInCookieConnectRequest,
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInConnectResponse:
    """
    Connect to LinkedIn using li_at session cookie.
    This is the recommended primary method - bypasses all login challenges.
    Requires admin role.
    """
    try:
        return await service.connect_with_cookie(request.cookie)
    except LinkedInBrowserBusyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/open-browser", response_model=LinkedInConnectResponse)
async def open_browser_for_manual_login(
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInConnectResponse:
    """
    Open visible browser for manual login.
    Use this as fallback when cookie auth fails or expires.
    After logging in manually, call /validate-session to confirm.
    Requires admin role.
    """
    try:
        return await service.open_browser_for_manual_login()
    except LinkedInBrowserBusyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/verify-code", response_model=LinkedInConnectResponse)
async def verify_code(
    request: LinkedInVerifyCodeRequest,
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInConnectResponse:
    """
    Submit verification code.
    Requires admin role.
    """
    try:
        return await service.verify_code(request.code)
    except LinkedInBrowserNotRunningError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except LinkedInBrowserBusyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/search", response_model=LinkedInSearchResponse)
async def search(
    request: LinkedInSearchRequest,
    _: Annotated[dict, Depends(get_current_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInSearchResponse:
    """
    Search for contacts on LinkedIn.
    Requires authentication.

    Args:
        query: Search keywords
        limit: Max results (default 50, max 100)
    """
    try:
        return await service.search(request.query, limit=request.limit)
    except LinkedInRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
        )
    except LinkedInNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except LinkedInBrowserBusyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/search-companies", response_model=LinkedInCompanySearchResponse)
async def search_by_companies(
    request: LinkedInCompanySearchRequest,
    _: Annotated[dict, Depends(get_current_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInCompanySearchResponse:
    """
    Search for contacts at specific companies from an Excel import.
    Requires authentication.

    Args:
        companies: List of company names from Excel
        keywords: Additional search keywords (e.g., "Directeur Marketing")
        limit_per_company: Max results per company (default 10)
    """
    try:
        return await service.search_by_companies(
            companies=request.companies,
            keywords=request.keywords,
            limit_per_company=request.limit_per_company,
        )
    except LinkedInRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
        )
    except LinkedInNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except LinkedInBrowserBusyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/disconnect")
async def disconnect(
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> dict:
    """
    Disconnect LinkedIn and clear credentials.
    Requires admin role.
    """
    await service.disconnect()
    return {"message": "LinkedIn disconnected successfully"}


@router.post("/close-browser")
async def close_browser(
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> dict:
    """
    Close the browser instance.
    Use this to reset the browser if it gets stuck.
    Requires admin role.
    """
    await service.close_browser()
    return {"message": "Browser closed successfully"}


@router.post("/validate-session", response_model=LinkedInConnectResponse)
async def validate_session(
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> LinkedInConnectResponse:
    """
    Validate existing browser session and update status.
    Use this if you manually logged in via the browser.
    Requires admin role.
    """
    try:
        return await service.validate_and_update_session()
    except LinkedInError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/search-stream", response_model=SearchSessionResponse)
async def start_search_stream(
    request: LinkedInCompanySearchRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> SearchSessionResponse:
    """
    Start a streaming search for contacts at companies.
    Returns a session ID that can be used to poll for results.
    The search runs in the background and results are saved to DB.
    """
    search_repo = SearchResultsRepository(db)
    user_id = str(user.get("_id", user.get("id", "unknown")))

    # Check for cached search
    cached = await search_repo.find_cached_search(
        user_id=user_id,
        companies=request.companies,
        keywords=request.keywords,
        max_age_hours=24,
    )

    if cached:
        return SearchSessionResponse(
            session_id=cached["_id"],
            status="completed",
            total_companies=cached.get("total_companies", len(request.companies)),
            message="Résultats en cache trouvés",
        )

    # Create new search session
    session_id = await search_repo.create_search_session(
        user_id=user_id,
        companies=request.companies,
        keywords=request.keywords,
    )

    # Start background search task
    background_tasks.add_task(
        run_background_search,
        session_id=session_id,
        companies=request.companies,
        keywords=request.keywords,
        limit_per_company=request.limit_per_company,
        db=db,
        service=service,
    )

    return SearchSessionResponse(
        session_id=session_id,
        status="in_progress",
        total_companies=len(request.companies),
        message="Recherche démarrée",
    )


async def run_background_search(
    session_id: str,
    companies: list[str],
    keywords: list[str],
    limit_per_company: int,
    db: AsyncIOMotorDatabase,
    service: LinkedInService,
) -> None:
    """Background task to run the search and save results."""
    import logging
    import random
    logger = logging.getLogger(__name__)

    search_repo = SearchResultsRepository(db)
    http_client = get_linkedin_http_client()
    rate_limiter = get_rate_limiter(db)
    searches_done = 0

    # Normalize keywords - ensure we have at least one (empty string means search by company only)
    if not keywords:
        keywords = [""]
    keywords = [k.strip() for k in keywords if k.strip()] or [""]

    total_searches = len(companies) * len(keywords)

    try:
        for company in companies:
            for keyword in keywords:
                # Check rate limit before each search
                can_search, reason = await rate_limiter.can_search()
                if not can_search:
                    logger.warning(f"Rate limit reached: {reason}. Pausing search.")
                    # Wait for cooldown and retry
                    await asyncio.sleep(60)  # Wait 1 minute then check again
                    can_search, reason = await rate_limiter.can_search()
                    if not can_search:
                        logger.error(f"Still rate limited after wait: {reason}")
                        await search_repo.complete_session(session_id, "rate_limited")
                        return

                # Build search query
                if keyword:
                    query = f"{keyword} {company}"
                else:
                    query = company

                logger.info(f"Searching ({searches_done + 1}/{total_searches}): {query}")

                try:
                    contacts = await http_client.search_people(
                        query,
                        limit=limit_per_company,
                        company_filter=company,
                        keywords_filter=keyword if keyword else None,
                    )

                    # Record search for rate limiting
                    await rate_limiter.record_search()
                    searches_done += 1

                    # Convert to SearchResultDocument
                    results = [
                        SearchResultDocument(
                            name=c.name,
                            title=c.title,
                            company=c.company or company,
                            location=c.location,
                            profile_url=c.profile_url,
                            searched_company=company,
                            searched_keywords=keyword,
                        )
                        for c in contacts
                    ]

                    # Save results to DB
                    await search_repo.add_results(session_id, results, company)

                except Exception as e:
                    logger.error(f"Error searching {query}: {e}")

                # Human-like delay between searches to avoid rate limiting
                if total_searches > 1:
                    delay = random.uniform(2.0, 5.0)
                    # Occasional longer pause like a human taking a break
                    if searches_done % 5 == 0:
                        delay += random.uniform(3.0, 8.0)
                        logger.info(f"Taking a longer break ({delay:.1f}s) after {searches_done} searches")
                    await asyncio.sleep(delay)

        # Mark as completed
        await search_repo.complete_session(session_id, "completed")

    except Exception as e:
        logger.error(f"Background search failed: {e}")
        await search_repo.complete_session(session_id, "failed")


@router.get("/search-session/{session_id}/status", response_model=SearchSessionStatusResponse)
async def get_search_session_status(
    session_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SearchSessionStatusResponse:
    """Get the status of a search session."""
    search_repo = SearchResultsRepository(db)
    session = await search_repo.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Handle keywords (can be list or string)
    keywords = session.get("keywords", [])
    if isinstance(keywords, list):
        keywords_str = ", ".join(keywords)
    else:
        keywords_str = keywords or ""

    return SearchSessionStatusResponse(
        session_id=session_id,
        status=session.get("status", "unknown"),
        companies_searched=session.get("companies_searched", 0),
        total_companies=session.get("total_companies", 0),
        total_results=len(session.get("results", [])),
        keywords=keywords_str,
        created_at=str(session.get("created_at", "")),
    )


@router.get("/search-session/{session_id}/results", response_model=SearchResultsPageResponse)
async def get_search_session_results(
    session_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SearchResultsPageResponse:
    """Get paginated results from a search session."""
    search_repo = SearchResultsRepository(db)
    data = await search_repo.get_session_results(session_id, page, page_size)

    # Convert results to LinkedInContact format
    contacts = [
        LinkedInContact(
            name=r.get("name"),
            title=r.get("title"),
            company=r.get("company"),
            location=r.get("location"),
            profile_url=r.get("profile_url"),
        )
        for r in data["results"]
    ]

    return SearchResultsPageResponse(
        results=contacts,
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
        companies_searched=data["companies_searched"],
        total_companies=data["total_companies"],
        status=data["status"],
    )


@router.get("/search-history")
async def get_search_history(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> dict:
    """Get user's search history."""
    search_repo = SearchResultsRepository(db)
    user_id = str(user.get("_id", user.get("id", "unknown")))

    return await search_repo.get_user_searches(user_id, page, page_size)


@router.post("/debug-search")
async def debug_search(
    request: LinkedInSearchRequest,
    _: Annotated[dict, Depends(get_current_admin_user)],
    service: Annotated[LinkedInService, Depends(get_linkedin_service)],
) -> dict:
    """
    Debug endpoint to see raw HTML from LinkedIn search.
    Requires admin role.
    """
    from urllib.parse import quote

    http_client = get_linkedin_http_client()
    if not http_client.has_cookie():
        raise HTTPException(status_code=400, detail="No cookie set")

    client = await http_client._get_client()
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(request.query)}"

    html_headers = {
        "User-Agent": http_client.DEFAULT_HEADERS["User-Agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    response = await client.get(search_url, headers=html_headers)

    # Save HTML to file for inspection
    with open("/tmp/linkedin_search_debug.html", "w") as f:
        f.write(response.text)

    # Return summary
    html = response.text
    return {
        "status_code": response.status_code,
        "url": str(response.url),
        "html_size": len(html),
        "has_firstName": "firstName" in html,
        "has_publicIdentifier": "publicIdentifier" in html,
        "has_miniProfile": "miniProfile" in html,
        "has_searchResults": "searchResults" in html,
        "has_included": '"included"' in html,
        "saved_to": "/tmp/linkedin_search_debug.html",
        "first_500_chars": html[:500],
    }


@router.get("/rate-limit-status")
async def get_rate_limit_status(
    _: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> dict:
    """
    Get current rate limit status.
    Shows remaining searches for today/this hour and session info.
    """
    rate_limiter = get_rate_limiter(db)
    return await rate_limiter.get_status()


@router.post("/reset-rate-limits")
async def reset_rate_limits(
    _: Annotated[dict, Depends(get_current_admin_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> dict:
    """
    Reset rate limit counters.
    Requires admin role.
    """
    rate_limiter = get_rate_limiter(db)
    return await rate_limiter.reset_limits()
