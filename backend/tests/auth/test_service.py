import pytest
from unittest.mock import AsyncMock, MagicMock

from app.auth.service import AuthService
from app.auth.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.users.model import UserRole


@pytest.fixture
def mock_user_repository():
    """Provide a mock user repository."""
    return AsyncMock()


@pytest.fixture
def mock_password_hasher():
    """Provide a mock password hasher."""
    hasher = MagicMock()
    hasher.hash.return_value = "hashed_password"
    hasher.verify.return_value = True
    return hasher


@pytest.fixture
def mock_jwt_service():
    """Provide a mock JWT service."""
    service = MagicMock()
    service.create_access_token.return_value = "access_token"
    service.create_refresh_token.return_value = "refresh_token"
    service.decode_token.return_value = {"sub": "user_id", "type": "access"}
    return service


@pytest.fixture
def auth_service(mock_user_repository, mock_password_hasher, mock_jwt_service):
    """Provide an AuthService with mocked dependencies."""
    return AuthService(
        user_repository=mock_user_repository,
        password_hasher=mock_password_hasher,
        jwt_service=mock_jwt_service,
    )


@pytest.mark.asyncio
async def test_register_creates_user_with_hashed_password(
    auth_service, mock_user_repository, mock_password_hasher
):
    """Test that register hashes password and creates user."""
    mock_user_repository.get_by_email.return_value = None
    mock_user_repository.count.return_value = 1  # Not first user
    mock_user_repository.create.return_value = {
        "_id": "user_id",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "hashed_password",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    }

    result = await auth_service.register(
        email="test@example.com",
        password="plainpassword",
        full_name="Test User",
    )

    mock_password_hasher.hash.assert_called_once_with("plainpassword")
    mock_user_repository.create.assert_called_once()
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_first_user_becomes_admin(
    auth_service, mock_user_repository, mock_password_hasher
):
    """Test that first registered user becomes admin and is auto-approved."""
    mock_user_repository.get_by_email.return_value = None
    mock_user_repository.count.return_value = 0  # First user
    mock_user_repository.create.return_value = {
        "_id": "user_id",
        "email": "first@example.com",
        "full_name": "First User",
        "hashed_password": "hashed_password",
        "role": UserRole.ADMIN.value,
        "is_approved": True,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    }

    await auth_service.register(
        email="first@example.com",
        password="password123",
        full_name="First User",
    )

    # Verify create was called with admin role and is_approved=True
    create_call = mock_user_repository.create.call_args[0][0]
    assert create_call["role"] == UserRole.ADMIN.value
    assert create_call["is_approved"] is True


@pytest.mark.asyncio
async def test_subsequent_user_is_not_admin(
    auth_service, mock_user_repository, mock_password_hasher
):
    """Test that subsequent users are not admin and require approval."""
    mock_user_repository.get_by_email.return_value = None
    mock_user_repository.count.return_value = 1  # Not first user
    mock_user_repository.create.return_value = {
        "_id": "user_id",
        "email": "second@example.com",
        "full_name": "Second User",
        "hashed_password": "hashed_password",
        "role": UserRole.USER.value,
        "is_approved": False,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    }

    await auth_service.register(
        email="second@example.com",
        password="password123",
        full_name="Second User",
    )

    # Verify create was called with user role and is_approved=False
    create_call = mock_user_repository.create.call_args[0][0]
    assert create_call["role"] == UserRole.USER.value
    assert create_call["is_approved"] is False


@pytest.mark.asyncio
async def test_register_fails_if_email_exists(auth_service, mock_user_repository):
    """Test that register raises error if email already exists."""
    mock_user_repository.get_by_email.return_value = {"email": "test@example.com"}

    with pytest.raises(UserAlreadyExistsError):
        await auth_service.register(
            email="test@example.com",
            password="plainpassword",
            full_name="Test User",
        )


@pytest.mark.asyncio
async def test_login_returns_tokens_for_valid_credentials(
    auth_service, mock_user_repository, mock_password_hasher, mock_jwt_service
):
    """Test that login returns tokens for valid credentials."""
    mock_user_repository.get_by_email.return_value = {
        "_id": "user_id",
        "email": "test@example.com",
        "hashed_password": "hashed_password",
        "is_active": True,
        "is_approved": True,
    }
    mock_password_hasher.verify.return_value = True

    result = await auth_service.login(
        email="test@example.com",
        password="correctpassword",
    )

    assert result["access_token"] == "access_token"
    assert result["refresh_token"] == "refresh_token"
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_fails_for_invalid_password(
    auth_service, mock_user_repository, mock_password_hasher
):
    """Test that login raises error for invalid password."""
    mock_user_repository.get_by_email.return_value = {
        "_id": "user_id",
        "email": "test@example.com",
        "hashed_password": "hashed_password",
        "is_active": True,
    }
    mock_password_hasher.verify.return_value = False

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            email="test@example.com",
            password="wrongpassword",
        )


@pytest.mark.asyncio
async def test_login_fails_for_nonexistent_user(auth_service, mock_user_repository):
    """Test that login raises error for non-existent user."""
    mock_user_repository.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            email="nonexistent@example.com",
            password="anypassword",
        )


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(
    auth_service, mock_user_repository, mock_jwt_service
):
    """Test that refresh returns new access token for valid refresh token."""
    mock_jwt_service.decode_token.return_value = {"sub": "user_id", "type": "refresh"}
    mock_user_repository.get_by_id.return_value = {
        "_id": "user_id",
        "email": "test@example.com",
        "is_active": True,
    }

    result = await auth_service.refresh_token("valid_refresh_token")

    assert result["access_token"] == "access_token"
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_fails_for_invalid_token(auth_service, mock_jwt_service):
    """Test that refresh raises error for invalid token."""
    mock_jwt_service.decode_token.return_value = None

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_token("invalid_token")


@pytest.mark.asyncio
async def test_refresh_fails_for_access_token(auth_service, mock_jwt_service):
    """Test that refresh raises error when access token is used instead of refresh."""
    mock_jwt_service.decode_token.return_value = {"sub": "user_id", "type": "access"}

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_token("access_token_not_refresh")


@pytest.mark.asyncio
async def test_get_current_user_returns_user(
    auth_service, mock_user_repository, mock_jwt_service
):
    """Test that get_current_user returns user for valid token."""
    mock_jwt_service.decode_token.return_value = {"sub": "user_id", "type": "access"}
    mock_user_repository.get_by_id.return_value = {
        "_id": "user_id",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
    }

    result = await auth_service.get_current_user("valid_access_token")

    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_user_fails_for_invalid_token(auth_service, mock_jwt_service):
    """Test that get_current_user raises error for invalid token."""
    mock_jwt_service.decode_token.return_value = None

    with pytest.raises(InvalidTokenError):
        await auth_service.get_current_user("invalid_token")
