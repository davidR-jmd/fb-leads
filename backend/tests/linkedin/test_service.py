"""Tests for LinkedIn service (TDD)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.linkedin.service import LinkedInService
from app.linkedin.schemas import LinkedInStatus, LinkedInContact
from app.linkedin.exceptions import (
    LinkedInNotConfiguredError,
    LinkedInBrowserBusyError,
    LinkedInBrowserNotRunningError,
)


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return AsyncMock()


@pytest.fixture
def mock_browser():
    """Create a mock browser."""
    browser = MagicMock()
    browser.is_running.return_value = False
    browser.is_busy.return_value = False
    browser.launch = AsyncMock()
    browser.close = AsyncMock()
    browser.login = AsyncMock(return_value=LinkedInStatus.CONNECTED)
    browser.submit_verification_code = AsyncMock(return_value=LinkedInStatus.CONNECTED)
    browser.validate_session = AsyncMock(return_value=True)
    browser.search_people = AsyncMock(return_value=[])
    return browser


@pytest.fixture
def mock_encryption():
    """Create a mock encryption service."""
    encryption = MagicMock()
    encryption.encrypt.return_value = "encrypted_password"
    encryption.decrypt.return_value = "plain_password"
    return encryption


@pytest.fixture
def service(mock_repository, mock_browser, mock_encryption):
    """Create a service with mocked dependencies."""
    return LinkedInService(
        repository=mock_repository,
        browser=mock_browser,
        encryption=mock_encryption,
    )


class TestLinkedInServiceGetStatus:
    """Test get_status method."""

    async def test_returns_disconnected_when_no_config(self, service, mock_repository):
        """Should return disconnected when no config exists."""
        mock_repository.get_config.return_value = None

        status = await service.get_status()

        assert status.status == LinkedInStatus.DISCONNECTED
        assert status.email is None

    async def test_returns_config_status(self, service, mock_repository):
        """Should return status from config."""
        mock_repository.get_config.return_value = {
            "email": "test@example.com",
            "status": "connected",
            "last_connected": "2024-01-01T00:00:00",
        }

        status = await service.get_status()

        assert status.status == LinkedInStatus.CONNECTED
        assert status.email == "test@example.com"


class TestLinkedInServiceConnect:
    """Test connect method."""

    async def test_connect_saves_credentials(
        self, service, mock_repository, mock_browser, mock_encryption
    ):
        """Should save encrypted credentials."""
        mock_browser.login.return_value = LinkedInStatus.CONNECTED

        result = await service.connect("test@example.com", "password123")

        mock_encryption.encrypt.assert_called_once_with("password123")
        mock_repository.save_config.assert_called_once()

    async def test_connect_launches_browser(self, service, mock_browser):
        """Should launch browser if not running."""
        mock_browser.is_running.return_value = False
        mock_browser.login.return_value = LinkedInStatus.CONNECTED

        await service.connect("test@example.com", "password123")

        mock_browser.launch.assert_called_once()

    async def test_connect_returns_status_from_login(self, service, mock_browser):
        """Should return status from browser login."""
        mock_browser.login.return_value = LinkedInStatus.NEED_EMAIL_CODE

        result = await service.connect("test@example.com", "password123")

        assert result.status == LinkedInStatus.NEED_EMAIL_CODE

    async def test_connect_updates_status_on_success(
        self, service, mock_repository, mock_browser
    ):
        """Should update status and last_connected on success."""
        mock_browser.login.return_value = LinkedInStatus.CONNECTED

        await service.connect("test@example.com", "password123")

        mock_repository.update_status.assert_called_with(LinkedInStatus.CONNECTED)
        mock_repository.update_last_connected.assert_called_once()

    async def test_connect_fails_when_browser_busy(self, service, mock_browser):
        """Should raise error when browser is busy."""
        mock_browser.is_busy.return_value = True

        with pytest.raises(LinkedInBrowserBusyError):
            await service.connect("test@example.com", "password123")


class TestLinkedInServiceVerifyCode:
    """Test verify_code method."""

    async def test_verify_submits_code_to_browser(self, service, mock_browser):
        """Should submit code to browser."""
        mock_browser.is_running.return_value = True

        await service.verify_code("123456")

        mock_browser.submit_verification_code.assert_called_once_with("123456")

    async def test_verify_fails_when_browser_not_running(self, service, mock_browser):
        """Should raise error when browser not running."""
        mock_browser.is_running.return_value = False

        with pytest.raises(LinkedInBrowserNotRunningError):
            await service.verify_code("123456")

    async def test_verify_updates_status_on_success(
        self, service, mock_repository, mock_browser
    ):
        """Should update status on successful verification."""
        mock_browser.is_running.return_value = True
        mock_browser.submit_verification_code.return_value = LinkedInStatus.CONNECTED

        await service.verify_code("123456")

        mock_repository.update_status.assert_called_with(LinkedInStatus.CONNECTED)
        mock_repository.update_last_connected.assert_called_once()


class TestLinkedInServiceSearch:
    """Test search method."""

    async def test_search_returns_contacts(self, service, mock_browser):
        """Should return contacts from browser search."""
        mock_browser.is_running.return_value = True
        expected_contacts = [
            LinkedInContact(name="John Doe", title="Developer"),
        ]
        mock_browser.search_people.return_value = expected_contacts

        result = await service.search("Developer Paris")

        assert result.contacts == expected_contacts
        assert result.query == "Developer Paris"

    async def test_search_fails_when_browser_not_running(
        self, service, mock_browser, mock_repository
    ):
        """Should raise error when browser not running and no config."""
        mock_browser.is_running.return_value = False
        mock_repository.get_config.return_value = None

        with pytest.raises(LinkedInNotConfiguredError):
            await service.search("Developer Paris")

    async def test_search_auto_reconnects_if_config_exists(
        self, service, mock_browser, mock_repository, mock_encryption
    ):
        """Should auto-reconnect if config exists but browser not running."""
        mock_browser.is_running.return_value = False
        mock_repository.get_config.return_value = {
            "email": "test@example.com",
            "encrypted_password": "encrypted",
            "status": "connected",
        }
        mock_browser.login.return_value = LinkedInStatus.CONNECTED
        mock_browser.search_people.return_value = []

        # After reconnect, browser should be running
        def update_running_state(*args, **kwargs):
            mock_browser.is_running.return_value = True
            return LinkedInStatus.CONNECTED

        mock_browser.login.side_effect = update_running_state

        result = await service.search("Developer Paris")

        mock_browser.launch.assert_called_once()
        mock_browser.login.assert_called_once()

    async def test_search_fails_when_browser_busy(self, service, mock_browser):
        """Should raise error when browser is busy."""
        mock_browser.is_running.return_value = True
        mock_browser.is_busy.return_value = True

        with pytest.raises(LinkedInBrowserBusyError):
            await service.search("Developer Paris")


class TestLinkedInServiceDisconnect:
    """Test disconnect method."""

    async def test_disconnect_closes_browser(self, service, mock_browser):
        """Should close browser."""
        await service.disconnect()

        mock_browser.close.assert_called_once()

    async def test_disconnect_deletes_config(self, service, mock_repository):
        """Should delete config from repository."""
        await service.disconnect()

        mock_repository.delete_config.assert_called_once()


class TestLinkedInServiceInitialize:
    """Test initialize method (called on server start)."""

    async def test_initialize_does_nothing_when_no_config(
        self, service, mock_repository, mock_browser
    ):
        """Should not launch browser when no config."""
        mock_repository.get_config.return_value = None

        await service.initialize()

        mock_browser.launch.assert_not_called()

    async def test_initialize_launches_browser_when_connected(
        self, service, mock_repository, mock_browser
    ):
        """Should launch browser and validate when status is connected."""
        mock_repository.get_config.return_value = {
            "email": "test@example.com",
            "encrypted_password": "encrypted",
            "status": "connected",
        }
        mock_browser.validate_session.return_value = True

        await service.initialize()

        mock_browser.launch.assert_called_once()
        mock_browser.validate_session.assert_called_once()

    async def test_initialize_marks_disconnected_if_session_invalid(
        self, service, mock_repository, mock_browser
    ):
        """Should mark as disconnected if session validation fails."""
        mock_repository.get_config.return_value = {
            "email": "test@example.com",
            "encrypted_password": "encrypted",
            "status": "connected",
        }
        mock_browser.validate_session.return_value = False

        await service.initialize()

        mock_repository.update_status.assert_called_with(LinkedInStatus.DISCONNECTED)
