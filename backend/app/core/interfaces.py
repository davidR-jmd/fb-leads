from abc import ABC, abstractmethod
from typing import Any


class IPasswordHasher(ABC):
    """Interface for password hashing operations (Interface Segregation)."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plain text password."""
        pass

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed one."""
        pass


class ITokenService(ABC):
    """Interface for JWT token operations (Interface Segregation)."""

    @abstractmethod
    def create_access_token(self, data: dict[str, Any]) -> str:
        """Create a new access token."""
        pass

    @abstractmethod
    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Create a new refresh token."""
        pass

    @abstractmethod
    def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a token. Returns None if invalid."""
        pass


class IUserRepository(ABC):
    """Interface for user data access (Interface Segregation)."""

    @abstractmethod
    async def create(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new user."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total users."""
        pass
