"""LinkedIn module interfaces (Interface Segregation Principle)."""

from abc import ABC, abstractmethod
from typing import Any

from app.linkedin.schemas import LinkedInContact, LinkedInStatus


class IEncryptionService(ABC):
    """Interface for encryption operations."""

    @abstractmethod
    def encrypt(self, plain_text: str) -> str:
        """Encrypt plain text."""
        pass

    @abstractmethod
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt encrypted text."""
        pass


class ILinkedInConfigRepository(ABC):
    """Interface for LinkedIn configuration data access."""

    @abstractmethod
    async def get_config(self) -> dict[str, Any] | None:
        """Get LinkedIn configuration."""
        pass

    @abstractmethod
    async def save_config(
        self, email: str, encrypted_password: str, status: LinkedInStatus
    ) -> dict[str, Any]:
        """Save or update LinkedIn configuration with credentials."""
        pass

    @abstractmethod
    async def save_cookie_config(
        self, encrypted_cookie: str, status: LinkedInStatus
    ) -> dict[str, Any]:
        """Save or update LinkedIn configuration with cookie auth."""
        pass

    @abstractmethod
    async def save_manual_config(self, status: LinkedInStatus) -> dict[str, Any]:
        """Save or update LinkedIn configuration for manual login."""
        pass

    @abstractmethod
    async def update_status(
        self, status: LinkedInStatus, error_message: str | None = None
    ) -> dict[str, Any] | None:
        """Update connection status."""
        pass

    @abstractmethod
    async def update_last_connected(self) -> dict[str, Any] | None:
        """Update last connected timestamp."""
        pass

    @abstractmethod
    async def delete_config(self) -> bool:
        """Delete LinkedIn configuration."""
        pass


class ILinkedInBrowser(ABC):
    """Interface for LinkedIn browser automation."""

    @abstractmethod
    async def launch(self, headless: bool | None = None) -> None:
        """Launch browser with persistent profile."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close browser."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if browser is running."""
        pass

    @abstractmethod
    async def login(self, email: str, password: str) -> LinkedInStatus:
        """
        Attempt to login to LinkedIn.
        Returns status: CONNECTED, NEED_EMAIL_CODE, NEED_MANUAL_LOGIN, or ERROR.
        """
        pass

    @abstractmethod
    async def inject_cookie(self, li_at_cookie: str) -> bool:
        """
        Inject li_at session cookie into browser.
        Returns True if cookie was set successfully.
        """
        pass

    @abstractmethod
    async def navigate_to_login(self) -> None:
        """Navigate to LinkedIn login page for manual login."""
        pass

    @abstractmethod
    async def submit_verification_code(self, code: str) -> LinkedInStatus:
        """Submit verification code. Returns CONNECTED or ERROR."""
        pass

    @abstractmethod
    async def validate_session(self) -> bool:
        """Check if current session is still valid."""
        pass

    @abstractmethod
    async def search_people(self, query: str) -> list[LinkedInContact]:
        """Search for people on LinkedIn."""
        pass

    @abstractmethod
    def is_busy(self) -> bool:
        """Check if browser is busy with an operation."""
        pass

    @abstractmethod
    def set_busy(self, busy: bool) -> None:
        """Set busy state."""
        pass
