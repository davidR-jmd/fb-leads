from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.users.model import UserRole


async def get_current_admin_user(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Dependency to ensure current user is an admin."""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
