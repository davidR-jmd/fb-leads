from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.users.repository import UserRepository
from app.users.schemas import UserResponse, UserUpdateRequest
from app.admin.dependencies import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])


def get_user_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> UserRepository:
    """Dependency injection for UserRepository."""
    return UserRepository(db)


def _user_to_response(user: dict[str, Any]) -> UserResponse:
    """Convert user document to UserResponse (DRY helper)."""
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user.get("role", "user"),
        is_active=user["is_active"],
        is_approved=user.get("is_approved", False),
        created_at=user["created_at"],
    )


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    _: Annotated[dict, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[UserResponse]:
    """Get all users (admin only)."""
    users = await user_repository.get_all_users()
    return [_user_to_response(user) for user in users]


@router.get("/users/pending", response_model=list[UserResponse])
async def get_pending_users(
    _: Annotated[dict, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[UserResponse]:
    """Get all users pending approval (admin only)."""
    users = await user_repository.get_pending_users()
    return [_user_to_response(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    _: Annotated[dict, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Update user (admin only). Used for approving users, changing roles, etc."""
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    user = await user_repository.update(user_id, update_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_response(user)


@router.post("/users/{user_id}/approve", response_model=UserResponse)
async def approve_user(
    user_id: str,
    _: Annotated[dict, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Approve a user (admin only)."""
    user = await user_repository.update(user_id, {"is_approved": True})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_response(user)


@router.post("/users/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: str,
    _: Annotated[dict, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Toggle user active status (admin only)."""
    user = await user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_status = not user.get("is_active", True)
    updated_user = await user_repository.update(user_id, {"is_active": new_status})

    return _user_to_response(updated_user)


@router.post("/users/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_user(
    user_id: str,
    _: Annotated[dict, Depends(get_current_admin_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    """Reject and delete a pending user (admin only)."""
    deleted = await user_repository.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
