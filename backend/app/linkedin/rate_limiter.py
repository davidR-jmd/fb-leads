"""LinkedIn rate limiter to prevent account blocking.

Implements human-like usage patterns with:
- Hourly search limits
- Daily search limits
- Session duration limits
- Automatic cooldown periods
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


def _ensure_utc_aware(dt: datetime | str | None) -> datetime | None:
    """Ensure a datetime is UTC-aware.

    Handles:
    - None values
    - ISO format strings
    - Offset-naive datetimes (assumes UTC)
    - Offset-aware datetimes (converts to UTC)
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        # Parse ISO format string
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        # Assume naive datetimes are UTC
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if different timezone
        dt = dt.astimezone(timezone.utc)

    return dt


class LinkedInRateLimiter:
    """Rate limiter for LinkedIn operations to prevent account blocking."""

    # Rate limits (balanced for active users while avoiding detection)
    MAX_SEARCHES_PER_HOUR = 50
    MAX_SEARCHES_PER_DAY = 300
    MAX_SESSION_DURATION_MINUTES = 60  # Force break after 60 minutes
    COOLDOWN_AFTER_SESSION_MINUTES = 10  # 10 min break between sessions

    RATE_LIMIT_DOC_ID = "linkedin_rate_limits"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["linkedin_rate_limits"]

    async def _get_rate_data(self) -> dict[str, Any]:
        """Get current rate limit data."""
        data = await self._collection.find_one({"_id": self.RATE_LIMIT_DOC_ID})
        if not data:
            data = await self._reset_rate_data()
        return data

    async def _reset_rate_data(self) -> dict[str, Any]:
        """Reset rate limit data for a new day."""
        now = datetime.now(timezone.utc)
        data = {
            "_id": self.RATE_LIMIT_DOC_ID,
            "searches_today": 0,
            "searches_this_hour": 0,
            "hour_started": now,
            "day_started": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "session_started": None,
            "last_search": None,
            "cooldown_until": None,
            "total_searches": 0,
        }
        await self._collection.replace_one(
            {"_id": self.RATE_LIMIT_DOC_ID}, data, upsert=True
        )
        return data

    async def can_search(self) -> tuple[bool, str | None]:
        """Check if a search is allowed.

        Returns:
            Tuple of (can_search, reason_if_blocked)
        """
        data = await self._get_rate_data()
        now = datetime.now(timezone.utc)

        # Check if in cooldown period
        cooldown_until = _ensure_utc_aware(data.get("cooldown_until"))
        if cooldown_until and now < cooldown_until:
            remaining = int((cooldown_until - now).total_seconds() // 60)
            return False, f"In cooldown period. Please wait {remaining} minutes."

        # Check daily limit
        day_started = _ensure_utc_aware(data.get("day_started"))
        if day_started:
            # Reset if new day
            if now.date() > day_started.date():
                await self._reset_daily_counts()
                data = await self._get_rate_data()

        if data.get("searches_today", 0) >= self.MAX_SEARCHES_PER_DAY:
            return False, f"Daily limit reached ({self.MAX_SEARCHES_PER_DAY} searches). Try again tomorrow."

        # Check hourly limit
        hour_started = _ensure_utc_aware(data.get("hour_started"))
        if hour_started:
            # Reset if new hour
            if (now - hour_started).total_seconds() >= 3600:
                await self._reset_hourly_counts()
                data = await self._get_rate_data()

        if data.get("searches_this_hour", 0) >= self.MAX_SEARCHES_PER_HOUR:
            return False, f"Hourly limit reached ({self.MAX_SEARCHES_PER_HOUR} searches). Please wait."

        # Check session duration
        session_started = _ensure_utc_aware(data.get("session_started"))
        if session_started:
            session_duration = (now - session_started).total_seconds() / 60
            if session_duration >= self.MAX_SESSION_DURATION_MINUTES:
                # Force cooldown
                cooldown_until = now + timedelta(minutes=self.COOLDOWN_AFTER_SESSION_MINUTES)
                await self._collection.update_one(
                    {"_id": self.RATE_LIMIT_DOC_ID},
                    {"$set": {"cooldown_until": cooldown_until, "session_started": None}}
                )
                return False, f"Session limit reached ({self.MAX_SESSION_DURATION_MINUTES} min). Taking a {self.COOLDOWN_AFTER_SESSION_MINUTES} min break."

        return True, None

    async def record_search(self) -> None:
        """Record a search operation."""
        now = datetime.now(timezone.utc)
        data = await self._get_rate_data()

        # Start session if not started
        update = {
            "$inc": {
                "searches_today": 1,
                "searches_this_hour": 1,
                "total_searches": 1,
            },
            "$set": {
                "last_search": now,
            }
        }

        if not data.get("session_started"):
            update["$set"]["session_started"] = now

        await self._collection.update_one(
            {"_id": self.RATE_LIMIT_DOC_ID},
            update
        )

        logger.info(
            f"Search recorded. Today: {data.get('searches_today', 0) + 1}/{self.MAX_SEARCHES_PER_DAY}, "
            f"This hour: {data.get('searches_this_hour', 0) + 1}/{self.MAX_SEARCHES_PER_HOUR}"
        )

    async def _reset_daily_counts(self) -> None:
        """Reset daily counters."""
        now = datetime.now(timezone.utc)
        await self._collection.update_one(
            {"_id": self.RATE_LIMIT_DOC_ID},
            {
                "$set": {
                    "searches_today": 0,
                    "day_started": now.replace(hour=0, minute=0, second=0, microsecond=0),
                }
            }
        )
        logger.info("Daily search counts reset")

    async def _reset_hourly_counts(self) -> None:
        """Reset hourly counters."""
        now = datetime.now(timezone.utc)
        await self._collection.update_one(
            {"_id": self.RATE_LIMIT_DOC_ID},
            {
                "$set": {
                    "searches_this_hour": 0,
                    "hour_started": now,
                }
            }
        )
        logger.info("Hourly search counts reset")

    async def end_session(self) -> None:
        """End current session and start cooldown."""
        now = datetime.now(timezone.utc)
        cooldown_until = now + timedelta(minutes=self.COOLDOWN_AFTER_SESSION_MINUTES)

        await self._collection.update_one(
            {"_id": self.RATE_LIMIT_DOC_ID},
            {
                "$set": {
                    "session_started": None,
                    "cooldown_until": cooldown_until,
                }
            }
        )
        logger.info(f"Session ended. Cooldown until {cooldown_until}")

    async def get_status(self) -> dict[str, Any]:
        """Get current rate limit status."""
        data = await self._get_rate_data()
        now = datetime.now(timezone.utc)

        # Calculate remaining
        searches_remaining_today = max(0, self.MAX_SEARCHES_PER_DAY - data.get("searches_today", 0))
        searches_remaining_hour = max(0, self.MAX_SEARCHES_PER_HOUR - data.get("searches_this_hour", 0))

        # Session duration
        session_started = _ensure_utc_aware(data.get("session_started"))
        session_minutes = 0
        if session_started:
            session_minutes = int((now - session_started).total_seconds() / 60)

        # Cooldown
        cooldown_until = _ensure_utc_aware(data.get("cooldown_until"))
        cooldown_remaining = 0
        if cooldown_until and now < cooldown_until:
            cooldown_remaining = int((cooldown_until - now).total_seconds() / 60)

        return {
            "searches_today": data.get("searches_today", 0),
            "searches_this_hour": data.get("searches_this_hour", 0),
            "searches_remaining_today": searches_remaining_today,
            "searches_remaining_hour": searches_remaining_hour,
            "session_duration_minutes": session_minutes,
            "max_session_minutes": self.MAX_SESSION_DURATION_MINUTES,
            "cooldown_remaining_minutes": cooldown_remaining,
            "total_searches": data.get("total_searches", 0),
            "limits": {
                "per_hour": self.MAX_SEARCHES_PER_HOUR,
                "per_day": self.MAX_SEARCHES_PER_DAY,
                "session_minutes": self.MAX_SESSION_DURATION_MINUTES,
            }
        }


# Singleton instance holder
_rate_limiter: LinkedInRateLimiter | None = None


def get_rate_limiter(db: AsyncIOMotorDatabase) -> LinkedInRateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LinkedInRateLimiter(db)
    return _rate_limiter
