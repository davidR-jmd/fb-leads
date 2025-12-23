"""LinkedIn search results repository."""

from datetime import datetime, timezone
from typing import Any
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.linkedin.models import SearchResultDocument


class SearchResultsRepository:
    """MongoDB repository for LinkedIn search results."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["linkedin_searches"]

    async def create_search_session(
        self,
        user_id: str,
        companies: list[str],
        keywords: list[str] | None = None,
    ) -> str:
        """Create a new search session and return its ID."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Normalize keywords
        if keywords is None:
            keywords = []
        keywords = [k.strip() for k in keywords if k.strip()]

        # Calculate total searches (companies × keywords)
        total_searches = len(companies) * max(len(keywords), 1)

        document = {
            "_id": session_id,
            "user_id": user_id,
            "companies": companies,
            "keywords": keywords,
            "status": "in_progress",
            "results": [],
            "companies_searched": 0,
            "total_companies": total_searches,  # Now represents total searches (companies × keywords)
            "created_at": now,
            "updated_at": now,
        }

        await self._collection.insert_one(document)
        return session_id

    async def add_results(
        self,
        session_id: str,
        results: list[SearchResultDocument],
        company_searched: str,
    ) -> None:
        """Add results for a company to an existing session."""
        now = datetime.now(timezone.utc)

        # Convert results to dicts
        result_dicts = [r.model_dump() for r in results]

        await self._collection.update_one(
            {"_id": session_id},
            {
                "$push": {"results": {"$each": result_dicts}},
                "$inc": {"companies_searched": 1},
                "$set": {"updated_at": now},
            },
        )

    async def complete_session(self, session_id: str, status: str = "completed") -> None:
        """Mark a search session as completed."""
        await self._collection.update_one(
            {"_id": session_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a search session by ID."""
        return await self._collection.find_one({"_id": session_id})

    async def get_session_results(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated results from a session."""
        session = await self._collection.find_one({"_id": session_id})

        if not session:
            return {"results": [], "total": 0, "page": page, "page_size": page_size}

        results = session.get("results", [])
        total = len(results)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]

        return {
            "results": paginated_results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "companies_searched": session.get("companies_searched", 0),
            "total_companies": session.get("total_companies", 0),
            "status": session.get("status", "unknown"),
        }

    async def find_cached_search(
        self,
        user_id: str,
        companies: list[str],
        keywords: list[str] | None = None,
        max_age_hours: int = 24,
    ) -> dict[str, Any] | None:
        """Find a cached search with the same parameters."""
        from datetime import timedelta

        min_date = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Normalize and sort for consistent comparison
        sorted_companies = sorted(companies)
        if keywords is None:
            keywords = []
        sorted_keywords = sorted([k.strip() for k in keywords if k.strip()])

        # Find completed searches with same params
        cursor = self._collection.find({
            "user_id": user_id,
            "status": "completed",
            "created_at": {"$gte": min_date},
        })

        async for session in cursor:
            session_companies = sorted(session.get("companies", []))
            session_keywords = session.get("keywords", [])
            # Handle both old string format and new list format
            if isinstance(session_keywords, str):
                session_keywords = [session_keywords] if session_keywords else []
            session_keywords_sorted = sorted([k.strip() for k in session_keywords if k.strip()])

            if session_companies == sorted_companies and session_keywords_sorted == sorted_keywords:
                return session

        return None

    async def get_user_searches(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Get user's search history with pagination."""
        skip = (page - 1) * page_size

        cursor = self._collection.find(
            {"user_id": user_id},
            {"results": 0},  # Exclude results for listing
        ).sort("created_at", -1).skip(skip).limit(page_size)

        sessions = await cursor.to_list(length=page_size)
        total = await self._collection.count_documents({"user_id": user_id})

        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
