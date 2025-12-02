from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.users.repository import UserRepository
from app.core.security import password_hasher, jwt_service
from app.auth.service import AuthService
from app.auth.exceptions import InvalidTokenError

security = HTTPBearer()


def get_auth_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AuthService:
    """Dependency injection for AuthService (Dependency Inversion Principle)."""
    user_repository = UserRepository(db)
    return AuthService(
        user_repository=user_repository,
        password_hasher=password_hasher,
        jwt_service=jwt_service,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """Dependency to get current authenticated user."""
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
