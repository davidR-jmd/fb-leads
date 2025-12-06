"""LinkedIn configuration repository (Single Responsibility)."""

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.linkedin.interfaces import ILinkedInConfigRepository
from app.linkedin.schemas import LinkedInStatus, LinkedInAuthMethod


class LinkedInConfigRepository(ILinkedInConfigRepository):
    """MongoDB repository for LinkedIn configuration (single document)."""

    CONFIG_ID = "linkedin_config"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["linkedin_config"]

    async def get_config(self) -> dict[str, Any] | None:
        """Get the LinkedIn configuration."""
        return await self._collection.find_one({"_id": self.CONFIG_ID})

    async def save_config(
        self, email: str, encrypted_password: str, status: LinkedInStatus
    ) -> dict[str, Any]:
        """Save or update LinkedIn configuration (upsert)."""
        now = datetime.now(timezone.utc)

        existing = await self.get_config()

        document = {
            "_id": self.CONFIG_ID,
            "email": email,
            "encrypted_password": encrypted_password,
            "status": status.value,
            "auth_method": LinkedInAuthMethod.CREDENTIALS.value,
            "error_message": None,
            "last_connected": existing.get("last_connected") if existing else None,
            "created_at": existing.get("created_at", now) if existing else now,
            "updated_at": now,
        }

        await self._collection.replace_one(
            {"_id": self.CONFIG_ID}, document, upsert=True
        )

        return document

    async def save_cookie_config(
        self, encrypted_cookie: str, status: LinkedInStatus
    ) -> dict[str, Any]:
        """Save LinkedIn configuration with cookie auth (upsert)."""
        now = datetime.now(timezone.utc)

        existing = await self.get_config()

        document = {
            "_id": self.CONFIG_ID,
            "encrypted_cookie": encrypted_cookie,
            "status": status.value,
            "auth_method": LinkedInAuthMethod.COOKIE.value,
            "error_message": None,
            "last_connected": existing.get("last_connected") if existing else None,
            "created_at": existing.get("created_at", now) if existing else now,
            "updated_at": now,
        }

        await self._collection.replace_one(
            {"_id": self.CONFIG_ID}, document, upsert=True
        )

        return document

    async def save_manual_config(self, status: LinkedInStatus) -> dict[str, Any]:
        """Save LinkedIn configuration for manual login (upsert)."""
        now = datetime.now(timezone.utc)

        existing = await self.get_config()

        document = {
            "_id": self.CONFIG_ID,
            "status": status.value,
            "auth_method": LinkedInAuthMethod.MANUAL.value,
            "error_message": None,
            "last_connected": existing.get("last_connected") if existing else None,
            "created_at": existing.get("created_at", now) if existing else now,
            "updated_at": now,
        }

        await self._collection.replace_one(
            {"_id": self.CONFIG_ID}, document, upsert=True
        )

        return document

    async def update_status(
        self, status: LinkedInStatus, error_message: str | None = None
    ) -> dict[str, Any] | None:
        """Update connection status."""
        update_data = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc),
        }

        if error_message is not None:
            update_data["error_message"] = error_message
        elif status != LinkedInStatus.ERROR:
            update_data["error_message"] = None

        result = await self._collection.find_one_and_update(
            {"_id": self.CONFIG_ID},
            {"$set": update_data},
            return_document=True,
        )

        return result

    async def update_last_connected(self) -> dict[str, Any] | None:
        """Update last connected timestamp."""
        result = await self._collection.find_one_and_update(
            {"_id": self.CONFIG_ID},
            {
                "$set": {
                    "last_connected": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=True,
        )

        return result

    async def delete_config(self) -> bool:
        """Delete LinkedIn configuration."""
        result = await self._collection.delete_one({"_id": self.CONFIG_ID})
        return result.deleted_count > 0
