"""Google Custom Search API client for finding LinkedIn profiles.

Google Custom Search API documentation:
https://developers.google.com/custom-search/v1/overview
"""

import logging
import re
from typing import Any

import httpx

from app.config import get_settings
from app.prospects.schemas import ContactData

logger = logging.getLogger(__name__)


class GoogleSearchClient:
    """Client for Google Custom Search API (finding LinkedIn profiles)."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cx: str) -> None:
        """Initialize Google Search client.

        Args:
            api_key: Google API key
            cx: Custom Search Engine ID (configured to search linkedin.com/in/*)
        """
        self._api_key = api_key
        self._cx = cx
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def find_linkedin_profile(
        self,
        job_function: str,
        company_name: str,
        max_results: int = 5,
    ) -> list[ContactData]:
        """Find LinkedIn profiles for a job function at a company.

        Args:
            job_function: Job title to search for (e.g., "Directeur Commercial")
            company_name: Company name (e.g., "Carrefour")
            max_results: Maximum number of profiles to return (default: 5)

        Returns:
            List of ContactData with LinkedIn URLs (empty list if none found)
        """
        if not self._api_key or not self._cx:
            logger.error("Google Search API key or CX not configured")
            return []

        try:
            client = await self._get_client()

            # Build search query targeting LinkedIn profiles
            query = f'{job_function} "{company_name}" site:linkedin.com/in'

            response = await client.get(
                self.BASE_URL,
                params={
                    "key": self._api_key,
                    "cx": self._cx,
                    "q": query,
                    "num": 10,  # Get top 10 results to filter
                },
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                contacts = []
                seen_urls = set()  # Avoid duplicates

                for item in items:
                    link = item.get("link", "")
                    if "linkedin.com/in/" in link:
                        contact = self._parse_result(item, job_function)
                        if contact and contact.linkedin_url and contact.linkedin_url not in seen_urls:
                            seen_urls.add(contact.linkedin_url)
                            contacts.append(contact)
                            if len(contacts) >= max_results:
                                break

                if not contacts:
                    logger.info(f"No LinkedIn profile found for: {job_function} at {company_name}")
                else:
                    logger.info(f"Found {len(contacts)} LinkedIn profiles for: {job_function} at {company_name}")

                return contacts

            elif response.status_code == 403:
                logger.error("Google Search API: Quota exceeded or invalid API key")
                return []

            elif response.status_code == 429:
                logger.warning("Google Search API: Rate limit exceeded")
                return []

            else:
                logger.error(f"Google Search API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Google Search API request failed: {e}")
            return []

    async def search_linkedin_profiles(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[ContactData]:
        """Search for LinkedIn profiles with a custom query.

        Args:
            query: Search query (will automatically add site:linkedin.com/in)
            num_results: Number of results to return (max 10 per request)

        Returns:
            List of ContactData with LinkedIn URLs
        """
        if not self._api_key or not self._cx:
            logger.error("Google Search API key or CX not configured")
            return []

        try:
            client = await self._get_client()

            # Ensure we're searching LinkedIn
            if "site:linkedin.com" not in query.lower():
                query = f"{query} site:linkedin.com/in"

            response = await client.get(
                self.BASE_URL,
                params={
                    "key": self._api_key,
                    "cx": self._cx,
                    "q": query,
                    "num": min(num_results, 10),
                },
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                contacts = []
                for item in items:
                    link = item.get("link", "")
                    if "linkedin.com/in/" in link:
                        contact = self._parse_result(item)
                        if contact:
                            contacts.append(contact)

                return contacts

            else:
                logger.error(f"Google Search API error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Google Search API request failed: {e}")
            return []

    def _parse_result(self, item: dict[str, Any], expected_title: str | None = None) -> ContactData | None:
        """Parse a Google Search result into ContactData.

        Args:
            item: Search result item from Google API
            expected_title: Expected job title (for validation)

        Returns:
            ContactData or None if parsing fails
        """
        try:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")

            # Extract name from title
            # Typical format: "Jean Dupont - Directeur Commercial - Carrefour | LinkedIn"
            name = self._extract_name_from_title(title)

            # Extract job title from the title or snippet
            job_title = self._extract_job_title(title, snippet)

            # Clean up LinkedIn URL (remove query params)
            linkedin_url = self._clean_linkedin_url(link)

            if not linkedin_url:
                return None

            return ContactData(
                name=name,
                title=job_title,
                linkedin_url=linkedin_url,
            )

        except Exception as e:
            logger.debug(f"Error parsing search result: {e}")
            return None

    def _extract_name_from_title(self, title: str) -> str | None:
        """Extract person name from Google result title.

        Args:
            title: Title like "Jean Dupont - Directeur Commercial - Carrefour | LinkedIn"

        Returns:
            Name or None
        """
        if not title:
            return None

        # Remove " | LinkedIn" suffix
        title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", title, flags=re.IGNORECASE)

        # Split by " - " and take the first part (usually the name)
        parts = title.split(" - ")
        if parts:
            name = parts[0].strip()
            # Validate it looks like a name (not too long, has letters)
            if name and len(name) < 60 and re.search(r"[a-zA-Z]", name):
                return name

        return None

    def _extract_job_title(self, title: str, snippet: str) -> str | None:
        """Extract job title from title or snippet.

        Args:
            title: Google result title
            snippet: Google result snippet

        Returns:
            Job title or None
        """
        # Try to extract from title first
        # Format: "Name - Job Title - Company | LinkedIn"
        title_clean = re.sub(r"\s*\|\s*LinkedIn\s*$", "", title, flags=re.IGNORECASE)
        parts = title_clean.split(" - ")

        if len(parts) >= 2:
            # Second part is usually the job title
            job_title = parts[1].strip()
            if job_title and len(job_title) < 100:
                return job_title

        # Try to extract from snippet
        # Look for common patterns
        if snippet:
            # Pattern: "Title chez Company" or "Title at Company"
            match = re.search(r"^([^·\n]+?)(?:\s+chez\s+|\s+at\s+)", snippet, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _clean_linkedin_url(self, url: str) -> str | None:
        """Clean LinkedIn URL by removing query parameters.

        Args:
            url: Raw LinkedIn URL

        Returns:
            Clean URL or None
        """
        if not url or "linkedin.com/in/" not in url:
            return None

        # Remove query parameters
        url = url.split("?")[0]

        # Ensure https
        if url.startswith("http://"):
            url = url.replace("http://", "https://")

        # Ensure proper format
        if not url.startswith("https://"):
            url = f"https://{url}"

        return url


# =============================================================================
# Singleton instance
# =============================================================================

_google_search_client: GoogleSearchClient | None = None


def get_google_search_client() -> GoogleSearchClient:
    """Get singleton Google Search client instance."""
    global _google_search_client
    if _google_search_client is None:
        settings = get_settings()
        _google_search_client = GoogleSearchClient(
            api_key=settings.google_search_api_key,
            cx=settings.google_search_cx,
        )
    return _google_search_client
