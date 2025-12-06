"""LinkedIn service - business logic (Single Responsibility)."""

import logging

from app.linkedin.interfaces import (
    ILinkedInConfigRepository,
    ILinkedInBrowser,
    IEncryptionService,
)
from app.linkedin.schemas import (
    LinkedInStatus,
    LinkedInAuthMethod,
    LinkedInStatusResponse,
    LinkedInConnectResponse,
    LinkedInSearchResponse,
)
from app.linkedin.exceptions import (
    LinkedInNotConfiguredError,
    LinkedInBrowserBusyError,
    LinkedInBrowserNotRunningError,
)
from app.linkedin.http_client import LinkedInHttpClient, get_linkedin_http_client

logger = logging.getLogger(__name__)


class LinkedInService:
    """LinkedIn business logic service (Dependency Inversion)."""

    def __init__(
        self,
        repository: ILinkedInConfigRepository,
        browser: ILinkedInBrowser,
        encryption: IEncryptionService,
    ) -> None:
        """Initialize with dependencies."""
        self._repository = repository
        self._browser = browser
        self._encryption = encryption

    async def initialize(self) -> None:
        """Initialize service on server start - auto-reconnect if needed."""
        config = await self._repository.get_config()

        if not config:
            logger.info("No LinkedIn config found, skipping initialization")
            return

        if config.get("status") != LinkedInStatus.CONNECTED.value:
            logger.info("LinkedIn not connected, skipping initialization")
            return

        try:
            logger.info("Attempting to restore LinkedIn session...")
            await self._browser.launch()

            if await self._browser.validate_session():
                logger.info("LinkedIn session restored successfully")
            else:
                logger.warning("LinkedIn session expired, marking as disconnected")
                await self._repository.update_status(LinkedInStatus.DISCONNECTED)
                await self._browser.close()

        except Exception as e:
            logger.error(f"Failed to restore LinkedIn session: {e}")
            await self._repository.update_status(LinkedInStatus.DISCONNECTED)

    async def get_status(self) -> LinkedInStatusResponse:
        """Get current LinkedIn connection status."""
        config = await self._repository.get_config()

        if not config:
            return LinkedInStatusResponse(status=LinkedInStatus.DISCONNECTED)

        auth_method = None
        if config.get("auth_method"):
            try:
                auth_method = LinkedInAuthMethod(config.get("auth_method"))
            except ValueError:
                pass

        return LinkedInStatusResponse(
            status=LinkedInStatus(config.get("status", "disconnected")),
            email=config.get("email"),
            last_connected=str(config.get("last_connected")) if config.get("last_connected") else None,
            error_message=config.get("error_message"),
            auth_method=auth_method,
        )

    async def connect(self, email: str, password: str) -> LinkedInConnectResponse:
        """Connect to LinkedIn with credentials."""
        if self._browser.is_busy():
            raise LinkedInBrowserBusyError()

        # Encrypt and save credentials
        encrypted_password = self._encryption.encrypt(password)
        await self._repository.save_config(
            email=email,
            encrypted_password=encrypted_password,
            status=LinkedInStatus.CONNECTING,
        )

        # Launch browser if needed
        if not self._browser.is_running():
            await self._browser.launch()

        # Attempt login
        status = await self._browser.login(email, password)

        # Update status based on result
        await self._repository.update_status(status)

        if status == LinkedInStatus.CONNECTED:
            await self._repository.update_last_connected()
            return LinkedInConnectResponse(
                status=status,
                message="Successfully connected to LinkedIn",
            )

        if status == LinkedInStatus.NEED_EMAIL_CODE:
            return LinkedInConnectResponse(
                status=status,
                message="Please enter the verification code sent to your email",
            )

        if status == LinkedInStatus.NEED_MANUAL_LOGIN:
            return LinkedInConnectResponse(
                status=status,
                message="Manual login required (captcha or phone verification)",
            )

        return LinkedInConnectResponse(
            status=LinkedInStatus.ERROR,
            message="Failed to connect - please check your credentials",
        )

    async def connect_with_cookie(self, cookie: str) -> LinkedInConnectResponse:
        """Connect to LinkedIn using li_at session cookie.

        This is the primary authentication method - most reliable as it
        bypasses all login challenges (CAPTCHA, 2FA, etc).

        Uses HTTP client directly (no browser) for better reliability.
        """
        # Validate cookie format
        cookie = cookie.strip()
        if len(cookie) < 100:
            return LinkedInConnectResponse(
                status=LinkedInStatus.ERROR,
                message=f"Cookie too short ({len(cookie)} chars). A valid li_at cookie is 300+ characters.",
            )

        # Get HTTP client and set cookie
        http_client = get_linkedin_http_client()
        http_client.set_cookie(cookie)

        # Validate session using HTTP client (no browser needed)
        logger.info("Validating cookie via HTTP client...")
        is_valid = await http_client.validate_session()

        if is_valid:
            # Save encrypted cookie
            encrypted_cookie = self._encryption.encrypt(cookie)
            await self._repository.save_cookie_config(
                encrypted_cookie=encrypted_cookie,
                status=LinkedInStatus.CONNECTED,
            )
            await self._repository.update_last_connected()

            logger.info("Connected to LinkedIn via cookie (HTTP client)")
            return LinkedInConnectResponse(
                status=LinkedInStatus.CONNECTED,
                message="Successfully connected to LinkedIn",
            )

        # Cookie is invalid or expired
        await self._repository.update_status(
            LinkedInStatus.ERROR,
            error_message="Cookie is invalid or expired",
        )
        return LinkedInConnectResponse(
            status=LinkedInStatus.ERROR,
            message="Cookie is invalid or expired - please get a fresh cookie from your browser",
        )

    async def open_browser_for_manual_login(self) -> LinkedInConnectResponse:
        """Open browser window for manual login.

        This is the fallback method - user logs in manually in the visible
        browser window, then clicks 'Validate Session' when done.
        """
        if self._browser.is_busy():
            raise LinkedInBrowserBusyError()

        # Save config with awaiting status
        await self._repository.save_manual_config(
            status=LinkedInStatus.AWAITING_MANUAL_LOGIN,
        )

        # Launch visible browser and navigate to login
        await self._browser.navigate_to_login()

        logger.info("Browser opened for manual login")
        return LinkedInConnectResponse(
            status=LinkedInStatus.AWAITING_MANUAL_LOGIN,
            message="Browser opened - please log in manually, then click 'Validate Session'",
        )

    async def verify_code(self, code: str) -> LinkedInConnectResponse:
        """Submit verification code."""
        if not self._browser.is_running():
            raise LinkedInBrowserNotRunningError()

        if self._browser.is_busy():
            raise LinkedInBrowserBusyError()

        status = await self._browser.submit_verification_code(code)

        await self._repository.update_status(status)

        if status == LinkedInStatus.CONNECTED:
            await self._repository.update_last_connected()
            return LinkedInConnectResponse(
                status=status,
                message="Verification successful",
            )

        return LinkedInConnectResponse(
            status=LinkedInStatus.ERROR,
            message="Invalid verification code",
        )

    async def search(self, query: str, limit: int = 50) -> LinkedInSearchResponse:
        """Search for contacts on LinkedIn.

        Args:
            query: Search query
            limit: Maximum number of results (default 50, max 100)
        """
        # Cap limit at 100 to avoid too many requests
        limit = min(limit, 100)

        # Check auth method and use appropriate client
        config = await self._repository.get_config()

        if not config:
            raise LinkedInNotConfiguredError()

        auth_method = config.get("auth_method")

        # If connected via cookie, use HTTP client (faster, no browser needed)
        if auth_method == LinkedInAuthMethod.COOKIE.value:
            http_client = get_linkedin_http_client()

            # Restore cookie if not set
            if not http_client.has_cookie():
                encrypted_cookie = config.get("encrypted_cookie")
                if encrypted_cookie:
                    cookie = self._encryption.decrypt(encrypted_cookie)
                    http_client.set_cookie(cookie)

            contacts = await http_client.search_people(query, limit=limit)
            return LinkedInSearchResponse(
                contacts=contacts,
                query=query,
                total_found=len(contacts),
            )

        # Otherwise use browser (for manual/credentials auth)
        if not self._browser.is_running():
            await self._auto_reconnect()

        if self._browser.is_busy():
            raise LinkedInBrowserBusyError()

        contacts = await self._browser.search_people(query)

        return LinkedInSearchResponse(
            contacts=contacts,
            query=query,
            total_found=len(contacts),
        )

    async def disconnect(self) -> None:
        """Disconnect LinkedIn and clear credentials."""
        await self._browser.close()
        await self._repository.delete_config()
        logger.info("LinkedIn disconnected and credentials cleared")

    async def close_browser(self) -> None:
        """Close browser instance - use to reset stuck browser."""
        await self._browser.close()
        logger.info("Browser closed manually")

    async def _auto_reconnect(self) -> None:
        """Attempt to auto-reconnect using saved credentials."""
        config = await self._repository.get_config()

        if not config:
            raise LinkedInNotConfiguredError()

        email = config.get("email")
        encrypted_password = config.get("encrypted_password")

        if not email or not encrypted_password:
            raise LinkedInNotConfiguredError()

        password = self._encryption.decrypt(encrypted_password)

        await self._browser.launch()
        status = await self._browser.login(email, password)

        if status != LinkedInStatus.CONNECTED:
            await self._repository.update_status(LinkedInStatus.DISCONNECTED)
            raise LinkedInNotConfiguredError()

        await self._repository.update_status(LinkedInStatus.CONNECTED)
        await self._repository.update_last_connected()

    async def validate_and_update_session(self) -> LinkedInConnectResponse:
        """Validate current browser session and update status in DB.

        Use this when you've manually logged in via the visible browser
        and want to sync the status with the app.
        """
        # Launch browser if not running
        if not self._browser.is_running():
            await self._browser.launch()

        # Check if session is valid
        is_valid = await self._browser.validate_session()

        if is_valid:
            await self._repository.update_status(LinkedInStatus.CONNECTED)
            await self._repository.update_last_connected()
            logger.info("Session validated and marked as connected")
            return LinkedInConnectResponse(
                status=LinkedInStatus.CONNECTED,
                message="Session validated - LinkedIn is connected",
            )
        else:
            await self._repository.update_status(LinkedInStatus.DISCONNECTED)
            logger.warning("Session validation failed - not logged in")
            return LinkedInConnectResponse(
                status=LinkedInStatus.DISCONNECTED,
                message="Session not valid - please log in",
            )
