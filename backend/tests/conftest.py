import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_database


@pytest_asyncio.fixture
async def mock_db():
    """Provide a mock MongoDB database for testing."""
    client = AsyncMongoMockClient()
    db = client["test_db"]
    yield db
    client.close()


@pytest_asyncio.fixture
async def test_client(mock_db):
    """Provide an async test client with mocked database."""
    app.dependency_overrides[get_database] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
