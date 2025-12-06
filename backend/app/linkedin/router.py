"""LinkedIn API router (Single Responsibility)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.admin.dependencies import get_current_admin_user
from app.linkedin.dependencies import get_linkedin_service
from app.linkedin.service import LinkedInService
from app.linkedin.schemas import (
    LinkedInConnectRequest,
    LinkedInCookieConnectRequest,
    LinkedInVerifyCodeRequest,
    LinkedInSearchRequest,
    LinkedInStatusResponse,
    LinkedInConnectResponse,
    LinkedInSearchResponse,
)
from app.linkedin.exceptions import (
    LinkedInBrowserBusyError,
    LinkedInBrowserNotRunningError,
    LinkedInNotConfiguredError,
    LinkedInError,
)

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
    from app.linkedin.http_client import get_linkedin_http_client
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
