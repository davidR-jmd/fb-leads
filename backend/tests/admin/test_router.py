import pytest
from app.users.model import UserRole


@pytest.fixture
def admin_data():
    """Sample admin user data for testing."""
    return {
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
    }


@pytest.fixture
def user_data():
    """Sample regular user data for testing."""
    return {
        "email": "user@example.com",
        "password": "UserPass123!",
        "full_name": "Regular User",
    }


async def create_admin_and_login(test_client, mock_db, admin_data):
    """Helper to create an admin user and get access token."""
    # Register admin
    await test_client.post("/auth/register", json=admin_data)

    # Update user to be admin and approved directly in DB
    await mock_db["users"].update_one(
        {"email": admin_data["email"]},
        {"$set": {"role": UserRole.ADMIN.value, "is_approved": True}}
    )

    # Login as admin
    response = await test_client.post(
        "/auth/login",
        json={"email": admin_data["email"], "password": admin_data["password"]},
    )
    return response.json()["access_token"]


async def create_user(test_client, user_data):
    """Helper to create a regular user."""
    response = await test_client.post("/auth/register", json=user_data)
    return response.json()


@pytest.mark.asyncio
async def test_get_all_users_requires_admin(test_client, user_data):
    """Test that GET /admin/users requires admin role."""
    # Register and login as regular user
    await test_client.post("/auth/register", json=user_data)

    # Try to access admin endpoint without admin token
    response = await test_client.get("/admin/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_all_users_as_admin(test_client, mock_db, admin_data, user_data):
    """Test GET /admin/users returns all users for admin."""
    admin_token = await create_admin_and_login(test_client, mock_db, admin_data)
    await create_user(test_client, user_data)

    response = await test_client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2
    emails = [u["email"] for u in users]
    assert admin_data["email"] in emails
    assert user_data["email"] in emails


@pytest.mark.asyncio
async def test_get_pending_users(test_client, mock_db, admin_data, user_data):
    """Test GET /admin/users/pending returns only pending users."""
    admin_token = await create_admin_and_login(test_client, mock_db, admin_data)
    await create_user(test_client, user_data)

    response = await test_client.get(
        "/admin/users/pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    users = response.json()
    # Admin is approved, so only regular user should be pending
    assert len(users) == 1
    assert users[0]["email"] == user_data["email"]
    assert users[0]["is_approved"] is False


@pytest.mark.asyncio
async def test_approve_user(test_client, mock_db, admin_data, user_data):
    """Test POST /admin/users/{id}/approve approves a user."""
    admin_token = await create_admin_and_login(test_client, mock_db, admin_data)
    created_user = await create_user(test_client, user_data)

    response = await test_client.post(
        f"/admin/users/{created_user['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_approved"] is True

    # Verify user can now login
    login_response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_reject_user(test_client, mock_db, admin_data, user_data):
    """Test POST /admin/users/{id}/reject deletes a user."""
    admin_token = await create_admin_and_login(test_client, mock_db, admin_data)
    created_user = await create_user(test_client, user_data)

    response = await test_client.post(
        f"/admin/users/{created_user['id']}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204

    # Verify user no longer exists
    login_response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_role(test_client, mock_db, admin_data, user_data):
    """Test PATCH /admin/users/{id} can update user role."""
    admin_token = await create_admin_and_login(test_client, mock_db, admin_data)
    created_user = await create_user(test_client, user_data)

    response = await test_client.patch(
        f"/admin/users/{created_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "admin", "is_approved": True},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["is_approved"] is True


@pytest.mark.asyncio
async def test_unapproved_user_cannot_login(test_client, mock_db, admin_data, user_data):
    """Test that unapproved users cannot login."""
    # First create admin (first user is auto-approved)
    await create_admin_and_login(test_client, mock_db, admin_data)
    # Then create regular user (will be unapproved)
    await create_user(test_client, user_data)

    response = await test_client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )

    assert response.status_code == 403
    assert "pending approval" in response.json()["detail"]
