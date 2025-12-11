"""LinkedIn module dependencies (Dependency Injection)."""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.database import get_database
from app.linkedin.repository import LinkedInConfigRepository
from app.linkedin.browser import LinkedInBrowser
from app.linkedin.encryption import AESEncryptionService
from app.linkedin.service import LinkedInService
from app.linkedin.rate_limiter import LinkedInRateLimiter, get_rate_limiter

settings = get_settings()


def get_encryption_service() -> AESEncryptionService:
    """Get encryption service."""
    return AESEncryptionService(secret_key=settings.linkedin_encryption_key)


def get_linkedin_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> LinkedInConfigRepository:
    """Get LinkedIn repository."""
    return LinkedInConfigRepository(db)


def get_linkedin_browser() -> LinkedInBrowser:
    """Get LinkedIn browser (singleton - thread-safe)."""
    return LinkedInBrowser(
        profile_path=settings.linkedin_browser_profile_path,
        headless=settings.linkedin_headless,
    )


def get_linkedin_service(
    repository: Annotated[LinkedInConfigRepository, Depends(get_linkedin_repository)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> LinkedInService:
    """Get LinkedIn service."""
    browser = get_linkedin_browser()
    encryption = get_encryption_service()
    rate_limiter = get_rate_limiter(db)
    return LinkedInService(
        repository=repository,
        browser=browser,
        encryption=encryption,
        rate_limiter=rate_limiter,
    )


async def initialize_linkedin_service(db: AsyncIOMotorDatabase) -> LinkedInService:
    """Initialize LinkedIn service with database (for startup)."""
    repository = LinkedInConfigRepository(db)
    browser = get_linkedin_browser()
    encryption = get_encryption_service()
    rate_limiter = get_rate_limiter(db)
    service = LinkedInService(
        repository=repository,
        browser=browser,
        encryption=encryption,
        rate_limiter=rate_limiter,
    )
    await service.initialize()
    return service


async def shutdown_linkedin_browser() -> None:
    """Shutdown LinkedIn browser (for cleanup)."""
    browser = LinkedInBrowser()  # Gets singleton instance
    if browser.is_running():
        await browser.close()
    LinkedInBrowser.reset_instance()
