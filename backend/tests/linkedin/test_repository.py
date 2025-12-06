"""Tests for LinkedIn configuration repository (TDD)."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.linkedin.repository import LinkedInConfigRepository
from app.linkedin.schemas import LinkedInStatus


@pytest_asyncio.fixture
async def mock_db():
    """Provide a mock MongoDB database for testing."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()


@pytest_asyncio.fixture
async def repository(mock_db):
    """Provide a repository instance."""
    return LinkedInConfigRepository(mock_db)


class TestLinkedInConfigRepository:
    """Test LinkedIn configuration repository."""

    async def test_get_config_returns_none_when_empty(self, repository):
        """Should return None when no config exists."""
        config = await repository.get_config()

        assert config is None

    async def test_save_config_creates_new_config(self, repository):
        """Should create a new configuration."""
        config = await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.DISCONNECTED,
        )

        assert config["email"] == "test@example.com"
        assert config["encrypted_password"] == "encrypted123"
        assert config["status"] == LinkedInStatus.DISCONNECTED.value
        assert "_id" in config

    async def test_get_config_returns_saved_config(self, repository):
        """Should return the saved configuration."""
        await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.DISCONNECTED,
        )

        config = await repository.get_config()

        assert config is not None
        assert config["email"] == "test@example.com"

    async def test_save_config_updates_existing_config(self, repository):
        """Should update existing configuration, not create new one."""
        await repository.save_config(
            email="old@example.com",
            encrypted_password="old_password",
            status=LinkedInStatus.DISCONNECTED,
        )

        await repository.save_config(
            email="new@example.com",
            encrypted_password="new_password",
            status=LinkedInStatus.CONNECTED,
        )

        config = await repository.get_config()

        assert config["email"] == "new@example.com"
        assert config["encrypted_password"] == "new_password"
        assert config["status"] == LinkedInStatus.CONNECTED.value

    async def test_update_status_changes_status(self, repository):
        """Should update only the status field."""
        await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.DISCONNECTED,
        )

        updated = await repository.update_status(LinkedInStatus.CONNECTED)

        assert updated is not None
        assert updated["status"] == LinkedInStatus.CONNECTED.value
        assert updated["email"] == "test@example.com"

    async def test_update_status_with_error_message(self, repository):
        """Should update status with error message."""
        await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.DISCONNECTED,
        )

        updated = await repository.update_status(
            LinkedInStatus.ERROR, error_message="Something went wrong"
        )

        assert updated is not None
        assert updated["status"] == LinkedInStatus.ERROR.value
        assert updated["error_message"] == "Something went wrong"

    async def test_update_status_returns_none_when_no_config(self, repository):
        """Should return None when no config exists."""
        updated = await repository.update_status(LinkedInStatus.CONNECTED)

        assert updated is None

    async def test_update_last_connected_sets_timestamp(self, repository):
        """Should update last_connected timestamp."""
        await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.CONNECTED,
        )

        updated = await repository.update_last_connected()

        assert updated is not None
        assert "last_connected" in updated
        assert updated["last_connected"] is not None

    async def test_update_last_connected_returns_none_when_no_config(self, repository):
        """Should return None when no config exists."""
        updated = await repository.update_last_connected()

        assert updated is None

    async def test_delete_config_removes_config(self, repository):
        """Should delete the configuration."""
        await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.DISCONNECTED,
        )

        result = await repository.delete_config()

        assert result is True
        assert await repository.get_config() is None

    async def test_delete_config_returns_false_when_no_config(self, repository):
        """Should return False when no config exists."""
        result = await repository.delete_config()

        assert result is False

    async def test_config_has_timestamps(self, repository):
        """Should have created_at and updated_at timestamps."""
        config = await repository.save_config(
            email="test@example.com",
            encrypted_password="encrypted123",
            status=LinkedInStatus.DISCONNECTED,
        )

        assert "created_at" in config
        assert "updated_at" in config
