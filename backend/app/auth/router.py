from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    AccessTokenResponse,
    RefreshRequest,
)
from app.auth.service import AuthService
from app.auth.dependencies import get_auth_service, get_current_user
from app.auth.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotApprovedError,
    UserDeactivatedError,
)
from app.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Register a new user."""
    try:
        user = await auth_service.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user.get("role", "user"),
            is_active=user["is_active"],
            is_approved=user.get("is_approved", False),
            created_at=user["created_at"],
        )
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Login and get access/refresh tokens."""
    try:
        tokens = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        return TokenResponse(**tokens)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    except UserNotApprovedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval by an administrator",
        )
    except UserDeactivatedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated",
        )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AccessTokenResponse:
    """Refresh access token using refresh token."""
    try:
        tokens = await auth_service.refresh_token(request.refresh_token)
        return AccessTokenResponse(**tokens)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user."""
    return UserResponse(
        id=str(current_user["_id"]),
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user.get("role", "user"),
        is_active=current_user["is_active"],
        is_approved=current_user.get("is_approved", False),
        created_at=current_user["created_at"],
    )
