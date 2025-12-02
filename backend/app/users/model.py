from datetime import datetime, timezone
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """User roles for authorization."""
    USER = "user"
    ADMIN = "admin"


def create_user_document(
    email: str,
    hashed_password: str,
    full_name: str,
    role: UserRole = UserRole.USER,
    is_approved: bool = False,
) -> dict[str, Any]:
    """Create a user document for MongoDB insertion."""
    now = datetime.now(timezone.utc)
    return {
        "email": email,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "role": role.value,
        "is_active": True,
        "is_approved": is_approved,
        "created_at": now,
        "updated_at": now,
    }
