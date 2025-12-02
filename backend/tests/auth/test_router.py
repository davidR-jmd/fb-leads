import pytest


@pytest.fixture
def user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
    }


async def approve_user(mock_db, email: str):
    """Helper to approve a user directly in the database."""
    await mock_db["users"].update_one(
        {"email": email},
        {"$set": {"is_approved": True}}
    )


@pytest.mark.asyncio
async def test_register_endpoint_creates_user(test_client, user_data):
    """Test POST /auth/register creates user successfully."""
    response = await test_client.post("/auth/register", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_endpoint_returns_422_for_invalid_data(test_client):
    """Test POST /auth/register returns 422 for invalid data."""
    response = await test_client.post(
        "/auth/register",
        json={"email": "invalid-email", "password": "pass"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_endpoint_returns_409_for_existing_email(test_client, user_data):
    """Test POST /auth/register returns 409 for duplicate email."""
    await test_client.post("/auth/register", json=user_data)

    response = await test_client.post("/auth/register", json=user_data)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_endpoint_returns_tokens(test_client, mock_db, user_data):
    """Test POST /auth/login returns tokens for valid credentials."""
    await test_client.post("/auth/register", json=user_data)
    await approve_user(mock_db, user_data["email"])

    response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_endpoint_returns_401_for_bad_credentials(test_client, user_data):
    """Test POST /auth/login returns 401 for invalid credentials."""
    await test_client.post("/auth/register", json=user_data)

    response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": "wrongpassword"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_endpoint_returns_401_for_nonexistent_user(test_client):
    """Test POST /auth/login returns 401 for non-existent user."""
    response = await test_client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "anypassword"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_returns_user(test_client, mock_db, user_data):
    """Test GET /auth/me returns current user."""
    await test_client.post("/auth/register", json=user_data)
    await approve_user(mock_db, user_data["email"])
    login_response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    access_token = login_response.json()["access_token"]

    response = await test_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_me_endpoint_returns_403_without_token(test_client):
    """Test GET /auth/me returns 403 without token (HTTPBearer returns 403 for missing token)."""
    response = await test_client.get("/auth/me")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_me_endpoint_returns_401_with_invalid_token(test_client):
    """Test GET /auth/me returns 401 with invalid token."""
    response = await test_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalidtoken"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_endpoint_returns_new_access_token(test_client, mock_db, user_data):
    """Test POST /auth/refresh returns new access token."""
    await test_client.post("/auth/register", json=user_data)
    await approve_user(mock_db, user_data["email"])
    login_response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await test_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_endpoint_returns_401_for_invalid_token(test_client):
    """Test POST /auth/refresh returns 401 for invalid token."""
    response = await test_client.post(
        "/auth/refresh",
        json={"refresh_token": "invalidtoken"},
    )

    assert response.status_code == 401
