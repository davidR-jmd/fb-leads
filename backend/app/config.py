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

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # LinkedIn
    linkedin_encryption_key: str = "change-this-key-in-production-32"
    linkedin_browser_profile_path: str = "./browser-profiles/linkedin"
    linkedin_headless: bool = True  # Set to False to see browser window (for debugging)

    # Pappers API (French company data)
    pappers_api_key: str = ""

    # Google Custom Search API (for finding LinkedIn profiles)
    google_search_api_key: str = ""
    google_search_cx: str = ""  # Custom Search Engine ID

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
