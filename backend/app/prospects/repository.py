"""Prospect Finder repository for MongoDB operations."""

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.prospects.schemas import (
    SearchStatus,
    SearchProgress,
    CompanyData,
    ContactData,
)
from app.prospects.models import (
    create_search_job_document,
    create_prospect_result_document,
    create_company_cache_document,
)

logger = logging.getLogger(__name__)


class ProspectRepository:
    """Repository for prospect search operations."""

    COLLECTION_JOBS = "prospect_search_jobs"
    COLLECTION_CACHE = "company_cache"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._jobs = db[self.COLLECTION_JOBS]
        self._cache = db[self.COLLECTION_CACHE]

    # =========================================================================
    # Search Jobs
    # =========================================================================

    async def create_search_job(
        self,
        user_id: str,
        job_function: str,
        company_name: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Create a new search job and return its ID."""
        from app.prospects.schemas import SearchMode, SearchFilters

        # Build filters if company_name provided
        search_filters = None
        if filters or company_name:
            filter_data = filters or {}
            if company_name:
                filter_data["company_name"] = company_name
            search_filters = SearchFilters(**filter_data)

        doc = create_search_job_document(
            user_id=user_id,
            job_function=job_function,
            mode=SearchMode.MANUAL,
            filters=search_filters,
        )

        result = await self._jobs.insert_one(doc)
        job_id = str(result.inserted_id)

        logger.info(f"Created search job {job_id} for user {user_id}")
        return job_id

    async def get_search_job(self, job_id: str) -> dict[str, Any] | None:
        """Get a search job by ID."""
        try:
            doc = await self._jobs.find_one({"_id": ObjectId(job_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Error getting search job {job_id}: {e}")
            return None

    async def update_job_status(
        self,
        job_id: str,
        status: SearchStatus,
        error_message: str | None = None,
    ) -> bool:
        """Update job status."""
        update = {
            "$set": {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc),
            }
        }

        if error_message:
            update["$set"]["error_message"] = error_message

        result = await self._jobs.update_one(
            {"_id": ObjectId(job_id)},
            update,
        )

        return result.modified_count > 0

    async def update_job_progress(
        self,
        job_id: str,
        progress: SearchProgress,
    ) -> bool:
        """Update job progress."""
        result = await self._jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "progress": progress.model_dump(),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return result.modified_count > 0

    async def add_result_to_job(
        self,
        job_id: str,
        company_data: CompanyData,
        contacts: list[ContactData] | None = None,
        searched_function: str = "",
        source: str = "pappers",
    ) -> bool:
        """Add a prospect result to a job with multiple contacts."""
        result_doc = create_prospect_result_document(
            company_data=company_data,
            contacts=contacts,
            searched_function=searched_function,
            source=source,
        )

        # Update progress counters
        inc_found = 1 if contacts and len(contacts) > 0 else 0

        result = await self._jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$push": {"results": result_doc},
                "$inc": {
                    "progress.processed": 1,
                    "progress.found": inc_found,
                },
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

        return result.modified_count > 0

    async def add_error_to_job(
        self,
        job_id: str,
        company_name: str,
    ) -> bool:
        """Record a failed company in the job."""
        result = await self._jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$push": {"failed_companies": company_name},
                "$inc": {
                    "progress.processed": 1,
                    "progress.errors": 1,
                },
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

        return result.modified_count > 0

    async def get_user_jobs(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Get search jobs for a user."""
        cursor = self._jobs.find(
            {"user_id": user_id},
            {
                "results": 0,  # Exclude results for listing
            },
        ).sort("created_at", -1).skip(skip).limit(limit)

        jobs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            jobs.append(doc)

        return jobs

    # =========================================================================
    # Company Cache
    # =========================================================================

    async def get_cached_company(self, siren: str) -> dict[str, Any] | None:
        """Get cached company data by SIREN."""
        doc = await self._cache.find_one({"_id": siren})

        if doc:
            # Check if expired
            expires_at = doc.get("expires_at")
            if expires_at and expires_at < datetime.now(timezone.utc):
                logger.debug(f"Cache expired for SIREN {siren}")
                return None

        return doc

    async def cache_company(
        self,
        siren: str,
        name: str,
        **kwargs: Any,
    ) -> bool:
        """Cache company data from Pappers."""
        doc = create_company_cache_document(siren=siren, name=name, **kwargs)

        result = await self._cache.replace_one(
            {"_id": siren},
            doc,
            upsert=True,
        )

        logger.debug(f"Cached company {name} (SIREN: {siren})")
        return result.acknowledged

    async def get_cached_company_by_name(self, name: str) -> dict[str, Any] | None:
        """Get cached company data by name (case-insensitive)."""
        doc = await self._cache.find_one({
            "name": {"$regex": f"^{name}$", "$options": "i"}
        })

        if doc:
            # Check if expired
            expires_at = doc.get("expires_at")
            if expires_at and expires_at < datetime.now(timezone.utc):
                return None

        return doc

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries. Returns count of deleted documents."""
        now = datetime.now(timezone.utc)

        result = await self._cache.delete_many({
            "expires_at": {"$lt": now}
        })

        if result.deleted_count > 0:
            logger.info(f"Cleaned up {result.deleted_count} expired cache entries")

        return result.deleted_count

    async def delete_old_jobs(self, days: int = 90) -> int:
        """Delete jobs older than specified days. Returns count of deleted jobs."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self._jobs.delete_many({
            "created_at": {"$lt": cutoff}
        })

        if result.deleted_count > 0:
            logger.info(f"Deleted {result.deleted_count} old search jobs")

        return result.deleted_count


# =============================================================================
# Singleton instance
# =============================================================================

_repository: ProspectRepository | None = None


def get_prospect_repository(db: AsyncIOMotorDatabase) -> ProspectRepository:
    """Get singleton repository instance."""
    global _repository
    if _repository is None:
        _repository = ProspectRepository(db)
    return _repository
