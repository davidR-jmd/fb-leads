"""Tests for LinkedIn router (TDD)."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.linkedin.dependencies import get_linkedin_service
from app.linkedin.schemas import (
    LinkedInStatus,
    LinkedInStatusResponse,
    LinkedInConnectResponse,
    LinkedInSearchResponse,
    LinkedInContact,
)
from app.linkedin.exceptions import (
    LinkedInBrowserBusyError,
    LinkedInBrowserNotRunningError,
    LinkedInNotConfiguredError,
)
from app.auth.dependencies import get_current_user
from app.admin.dependencies import get_current_admin_user


@pytest.fixture
def mock_linkedin_service():
    """Create a mock LinkedIn service."""
    service = AsyncMock()
    service.get_status.return_value = LinkedInStatusResponse(
        status=LinkedInStatus.DISCONNECTED
    )
    return service


@pytest.fixture
def mock_current_user():
    """Mock an authenticated user."""
    return {"_id": "user123", "email": "user@example.com", "role": "user"}


@pytest.fixture
def mock_admin_user():
    """Mock an admin user."""
    return {"_id": "admin123", "email": "admin@example.com", "role": "admin"}


@pytest_asyncio.fixture
async def client(mock_linkedin_service, mock_current_user, mock_admin_user):
    """Provide an async test client with mocked dependencies."""
    app.dependency_overrides[get_linkedin_service] = lambda: mock_linkedin_service
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


class TestGetStatus:
    """Test GET /linkedin/status endpoint."""

    async def test_returns_status(self, client, mock_linkedin_service):
        """Should return current status."""
        mock_linkedin_service.get_status.return_value = LinkedInStatusResponse(
            status=LinkedInStatus.CONNECTED,
            email="test@example.com",
        )

        response = await client.get("/linkedin/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["email"] == "test@example.com"

    async def test_requires_authentication(self, mock_linkedin_service):
        """Should require authentication."""
        app.dependency_overrides[get_linkedin_service] = lambda: mock_linkedin_service
        app.dependency_overrides.pop(get_current_user, None)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/linkedin/status")

        # Should return 401 or 403 when not authenticated
        assert response.status_code in [401, 403]

        app.dependency_overrides.clear()


class TestConnect:
    """Test POST /linkedin/connect endpoint."""

    async def test_connect_success(self, client, mock_linkedin_service):
        """Should connect successfully."""
        mock_linkedin_service.connect.return_value = LinkedInConnectResponse(
            status=LinkedInStatus.CONNECTED,
            message="Successfully connected",
        )

        response = await client.post(
            "/linkedin/connect",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"

    async def test_connect_requires_admin(self, mock_linkedin_service, mock_current_user):
        """Should require admin role."""
        app.dependency_overrides[get_linkedin_service] = lambda: mock_linkedin_service
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides.pop(get_current_admin_user, None)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/linkedin/connect",
                json={"email": "test@example.com", "password": "password123"},
            )

        # Should return 401 or 403 for non-admin
        assert response.status_code in [401, 403]

        app.dependency_overrides.clear()

    async def test_connect_returns_need_code(self, client, mock_linkedin_service):
        """Should return need_email_code status."""
        mock_linkedin_service.connect.return_value = LinkedInConnectResponse(
            status=LinkedInStatus.NEED_EMAIL_CODE,
            message="Enter verification code",
        )

        response = await client.post(
            "/linkedin/connect",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "need_email_code"

    async def test_connect_browser_busy(self, client, mock_linkedin_service):
        """Should return 409 when browser is busy."""
        mock_linkedin_service.connect.side_effect = LinkedInBrowserBusyError()

        response = await client.post(
            "/linkedin/connect",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 409


class TestVerifyCode:
    """Test POST /linkedin/verify-code endpoint."""

    async def test_verify_success(self, client, mock_linkedin_service):
        """Should verify code successfully."""
        mock_linkedin_service.verify_code.return_value = LinkedInConnectResponse(
            status=LinkedInStatus.CONNECTED,
            message="Verification successful",
        )

        response = await client.post(
            "/linkedin/verify-code",
            json={"code": "123456"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"

    async def test_verify_browser_not_running(self, client, mock_linkedin_service):
        """Should return 400 when browser not running."""
        mock_linkedin_service.verify_code.side_effect = LinkedInBrowserNotRunningError()

        response = await client.post(
            "/linkedin/verify-code",
            json={"code": "123456"},
        )

        assert response.status_code == 400


class TestSearch:
    """Test POST /linkedin/search endpoint."""

    async def test_search_returns_contacts(self, client, mock_linkedin_service):
        """Should return search results."""
        mock_linkedin_service.search.return_value = LinkedInSearchResponse(
            contacts=[
                LinkedInContact(name="John Doe", title="Developer"),
            ],
            query="Developer Paris",
            total_found=1,
        )

        response = await client.post(
            "/linkedin/search",
            json={"query": "Developer Paris"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["contacts"]) == 1
        assert data["contacts"][0]["name"] == "John Doe"

    async def test_search_not_configured(self, client, mock_linkedin_service):
        """Should return 400 when not configured."""
        mock_linkedin_service.search.side_effect = LinkedInNotConfiguredError()

        response = await client.post(
            "/linkedin/search",
            json={"query": "Developer Paris"},
        )

        assert response.status_code == 400

    async def test_search_browser_busy(self, client, mock_linkedin_service):
        """Should return 409 when browser is busy."""
        mock_linkedin_service.search.side_effect = LinkedInBrowserBusyError()

        response = await client.post(
            "/linkedin/search",
            json={"query": "Developer Paris"},
        )

        assert response.status_code == 409


class TestDisconnect:
    """Test POST /linkedin/disconnect endpoint."""

    async def test_disconnect_success(self, client, mock_linkedin_service):
        """Should disconnect successfully."""
        response = await client.post("/linkedin/disconnect")

        assert response.status_code == 200
        mock_linkedin_service.disconnect.assert_called_once()
