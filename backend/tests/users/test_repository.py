import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.users.repository import UserRepository


@pytest_asyncio.fixture
async def user_repository():
    """Provide a UserRepository with mock database."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    repo = UserRepository(db)
    yield repo
    client.close()


@pytest.mark.asyncio
async def test_create_user_stores_in_db(user_repository):
    """Test that create() stores user in database."""
    user_data = {
        "email": "test@example.com",
        "hashed_password": "hashed_password_here",
        "full_name": "Test User",
    }

    result = await user_repository.create(user_data)

    assert result is not None
    assert result["email"] == user_data["email"]
    assert result["full_name"] == user_data["full_name"]
    assert "_id" in result


@pytest.mark.asyncio
async def test_get_by_email_returns_user(user_repository):
    """Test that get_by_email() returns existing user."""
    user_data = {
        "email": "test@example.com",
        "hashed_password": "hashed_password_here",
        "full_name": "Test User",
    }
    await user_repository.create(user_data)

    result = await user_repository.get_by_email("test@example.com")

    assert result is not None
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_by_email_returns_none_if_not_found(user_repository):
    """Test that get_by_email() returns None for non-existent user."""
    result = await user_repository.get_by_email("nonexistent@example.com")

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_user(user_repository):
    """Test that get_by_id() returns existing user."""
    user_data = {
        "email": "test@example.com",
        "hashed_password": "hashed_password_here",
        "full_name": "Test User",
    }
    created = await user_repository.create(user_data)

    result = await user_repository.get_by_id(str(created["_id"]))

    assert result is not None
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_if_not_found(user_repository):
    """Test that get_by_id() returns None for non-existent user."""
    result = await user_repository.get_by_id("507f1f77bcf86cd799439011")

    assert result is None
