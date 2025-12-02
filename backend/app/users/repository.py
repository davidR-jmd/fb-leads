from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.interfaces import IUserRepository


class UserRepository(IUserRepository):
    """MongoDB user repository implementation (Single Responsibility)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["users"]

    async def create(self, user_data: dict[str, Any]) -> dict[str, Any]:
        result = await self._collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        return user_data

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"email": email})

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            return await self._collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    async def get_pending_users(self) -> list[dict[str, Any]]:
        """Get all users pending approval."""
        cursor = self._collection.find({"is_approved": False})
        return await cursor.to_list(length=None)

    async def get_all_users(self) -> list[dict[str, Any]]:
        """Get all users."""
        cursor = self._collection.find({})
        return await cursor.to_list(length=None)

    async def update(self, user_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a user by ID."""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = await self._collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_data},
                return_document=True,
            )
            return result
        except Exception:
            return None

    async def delete(self, user_id: str) -> bool:
        """Delete a user by ID."""
        try:
            result = await self._collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception:
            return False
