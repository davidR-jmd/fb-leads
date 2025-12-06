from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://admin:password@localhost:27017"
    mongodb_db_name: str = "fb_leads"

    # JWT
    jwt_secret_key: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # LinkedIn
    linkedin_encryption_key: str = "change-this-key-in-production-32"
    linkedin_browser_profile_path: str = "./browser-profiles/linkedin"
    linkedin_headless: bool = True  # Set to False to see browser window (for debugging)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
