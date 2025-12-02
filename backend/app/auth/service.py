from typing import Any

from app.core.interfaces import IPasswordHasher, ITokenService, IUserRepository
from app.users.model import create_user_document, UserRole
from app.auth.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotApprovedError,
    UserDeactivatedError,
)


class AuthService:
    """Authentication service (Single Responsibility - handles auth logic only)."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: IPasswordHasher,
        jwt_service: ITokenService,
    ) -> None:
        # Dependency Inversion - depends on abstractions
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._jwt_service = jwt_service

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> dict[str, Any]:
        """Register a new user. First user becomes admin and is auto-approved."""
        existing_user = await self._user_repository.get_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError(email)

        # First user becomes admin and is auto-approved
        user_count = await self._user_repository.count()
        is_first_user = user_count == 0

        hashed_password = self._password_hasher.hash(password)
        user_document = create_user_document(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=UserRole.ADMIN if is_first_user else UserRole.USER,
            is_approved=is_first_user,
        )

        return await self._user_repository.create(user_document)

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user and return tokens."""
        user = await self._user_repository.get_by_email(email)
        if not user:
            raise InvalidCredentialsError()

        if not self._password_hasher.verify(password, user["hashed_password"]):
            raise InvalidCredentialsError()

        # Check if user is approved (admins are always approved)
        if not user.get("is_approved", False) and user.get("role") != UserRole.ADMIN.value:
            raise UserNotApprovedError()

        # Check if user account is active
        if not user.get("is_active", True):
            raise UserDeactivatedError()

        user_id = str(user["_id"])
        return {
            "access_token": self._jwt_service.create_access_token({"sub": user_id}),
            "refresh_token": self._jwt_service.create_refresh_token({"sub": user_id}),
            "token_type": "bearer",
        }

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Generate new access token from refresh token."""
        payload = self._jwt_service.decode_token(refresh_token)
        if not payload:
            raise InvalidTokenError()

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid token type")

        user_id = payload.get("sub")
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("User not found")

        return {
            "access_token": self._jwt_service.create_access_token({"sub": user_id}),
            "token_type": "bearer",
        }

    async def get_current_user(self, access_token: str) -> dict[str, Any]:
        """Get current user from access token."""
        payload = self._jwt_service.decode_token(access_token)
        if not payload:
            raise InvalidTokenError()

        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        user_id = payload.get("sub")
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("User not found")

        return user
