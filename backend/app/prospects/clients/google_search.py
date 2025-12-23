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

    def _normalize_company_name(self, company_name: str) -> str:
        """Normalize company name for better LinkedIn search results.

        Removes legal suffixes and simplifies the name.
        """
        # Remove common French legal suffixes
        suffixes_to_remove = [
            r"\s+SAS$", r"\s+SARL$", r"\s+SA$", r"\s+EURL$", r"\s+SCI$",
            r"\s+SNC$", r"\s+SASU$", r"\s+SCOP$", r"\s+GIE$",
            r"\s+\(.*?\)$",  # Remove parenthetical suffixes like "(LYON)"
        ]
        normalized = company_name.upper()
        for pattern in suffixes_to_remove:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # Remove common prefixes
        prefixes_to_remove = [
            r"^SOCIETE\s+", r"^STE\s+", r"^GROUPE\s+", r"^ETS\s+",
            r"^ETABLISSEMENTS\s+", r"^LABORATOIRES?\s+",
        ]
        for pattern in prefixes_to_remove:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # If name is very long, take first 3-4 significant words
        words = normalized.split()
        if len(words) > 4:
            # Keep first 3 words that are not common filler words
            filler_words = {"ET", "DE", "DU", "DES", "LA", "LE", "LES", "D", "L", "A", "AU", "AUX"}
            significant_words = [w for w in words if w not in filler_words][:3]
            if significant_words:
                normalized = " ".join(significant_words)

        return normalized.strip()

    def _extract_brand_name(self, company_name: str) -> str:
        """Extract the brand/trade name from a company name.

        For complex legal names like "FNAC DARTY SA" or "CARREFOUR HYPERMARCHES",
        extracts just the brand name for better Google search results.

        Args:
            company_name: Full company name

        Returns:
            Brand name (first significant word)
        """
        normalized = self._normalize_company_name(company_name)

        # Common filler words to skip
        filler_words = {
            "ET", "DE", "DU", "DES", "LA", "LE", "LES", "D", "L", "A", "AU", "AUX",
            "FRANCE", "PARIS", "INTERNATIONAL", "EUROPE", "SERVICES", "SOLUTIONS",
            "CONSULTING", "TECHNOLOGIES", "GROUPE", "HOLDING", "DISTRIBUTION",
        }

        words = normalized.split()
        for word in words:
            if word not in filler_words and len(word) >= 3:
                return word

        # Fallback to first word
        return words[0] if words else company_name

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

        # Normalize company name and extract brand for better results
        normalized_name = self._normalize_company_name(company_name)
        brand_name = self._extract_brand_name(company_name)

        logger.info(f"Company search: original='{company_name}' | brand='{brand_name}' | normalized='{normalized_name}'")

        # Try multiple query strategies - prioritize simpler queries (brand name first)
        queries = [
            # Strategy 1: Brand name only (most likely to work)
            f'{job_function} {brand_name.lower()} site:linkedin.com',
            # Strategy 2: Normalized name
            f'{job_function} {normalized_name.lower()} site:linkedin.com',
        ]

        # Add original name if different
        if company_name.lower() != brand_name.lower() and company_name.lower() != normalized_name.lower():
            queries.append(f'{job_function} {company_name.lower()} site:linkedin.com')

        all_contacts: list[ContactData] = []
        seen_urls: set[str] = set()

        try:
            client = await self._get_client()

            for query in queries:
                if len(all_contacts) >= max_results:
                    break

                logger.info(f"Google Search query: {query}")

                response = await client.get(
                    self.BASE_URL,
                    params={
                        "key": self._api_key,
                        "cx": self._cx,
                        "q": query,
                        "num": 10,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    logger.info(f"Google returned {len(items)} results")

                    for item in items:
                        if len(all_contacts) >= max_results:
                            break

                        link = item.get("link", "")
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")[:100]

                        # Only accept personal profiles (/in/)
                        if "linkedin.com/in/" not in link:
                            logger.info(f"SKIP (not profile): {title} | {link}")
                            continue

                        # Validate company match
                        if not self._result_matches_company(item, company_name, normalized_name, brand_name):
                            logger.info(f"SKIP (company): {title} | {link}")
                            continue

                        # Job function validation is lenient - log but don't reject
                        job_match = self._result_matches_job_function(item, job_function)
                        if job_match:
                            logger.info(f"MATCH (exact): {title} | {link}")
                        else:
                            logger.info(f"MATCH (company only): {title} | {link}")

                        contact = self._parse_result(item, job_function)
                        if contact and contact.linkedin_url and contact.linkedin_url not in seen_urls:
                            seen_urls.add(contact.linkedin_url)
                            all_contacts.append(contact)

                    # If we found results with this query, stop trying other queries
                    if all_contacts:
                        break

                elif response.status_code == 403:
                    logger.error("Google Search API: Quota exceeded or invalid API key")
                    break

                elif response.status_code == 429:
                    logger.warning("Google Search API: Rate limit exceeded")
                    break

                else:
                    logger.warning(f"Google Search API error for query '{query}': {response.status_code}")
                    continue

            if not all_contacts:
                logger.info(f"No LinkedIn profile found for: {job_function} at {company_name} (normalized: {normalized_name})")
            else:
                logger.info(f"Found {len(all_contacts)} LinkedIn profiles for: {job_function} at {company_name}")

            return all_contacts

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

    def _result_matches_company(
        self,
        item: dict[str, Any],
        company_name: str,
        normalized_name: str,
        brand_name: str | None = None,
    ) -> bool:
        """Check if a Google search result matches the target company.

        Validates that the LinkedIn profile result actually belongs to someone
        working at the specified company by checking if the brand name appears
        in the title or snippet.

        Args:
            item: Google search result item
            company_name: Original company name
            normalized_name: Normalized company name
            brand_name: Extracted brand name (most important for matching)

        Returns:
            True if the result appears to match the company, False otherwise
        """
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        combined_text = f"{title} {snippet}"

        # Filter out common French words that shouldn't match alone
        stopwords = {
            "societe", "groupe", "france", "paris", "lyon", "marseille",
            "international", "consulting", "services", "solutions", "technologies",
            "chez", "the", "and", "les", "des", "pour", "avec", "holding",
            "distribution", "europe", "management",
        }

        # Priority 1: Check brand name (most reliable)
        if brand_name:
            brand_lower = brand_name.lower()
            if brand_lower not in stopwords and len(brand_lower) >= 3:
                if brand_lower in combined_text:
                    return True

        # Priority 2: Check normalized name words
        normalized_words = [w.lower() for w in normalized_name.split() if len(w) >= 3]
        for word in normalized_words:
            if word in stopwords:
                continue
            if word in combined_text:
                return True

        # Priority 3: Check original company name words
        company_words = [w.lower() for w in company_name.split() if len(w) >= 3]
        for word in company_words:
            if word in stopwords:
                continue
            if word in combined_text:
                return True

        return False

    def _result_matches_job_function(
        self,
        item: dict[str, Any],
        job_function: str,
    ) -> bool:
        """Check if a Google search result matches the target job function.

        Validates that the LinkedIn profile result shows someone with a matching
        job title by checking if ALL significant words from the job function
        appear in the title or snippet.

        Args:
            item: Google search result item
            job_function: Job function to search for (e.g., "Directeur Commercial")

        Returns:
            True if the result appears to match the job function, False otherwise
        """
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        combined_text = f"{title} {snippet}"

        job_lower = job_function.lower()

        # Common job function synonyms/abbreviations
        job_synonyms = {
            "directeur": ["director", "dir", "directrice", "dg"],
            "directrice": ["director", "dir", "directeur"],
            "commercial": ["sales", "vente", "ventes", "commerciale"],
            "commerciale": ["sales", "vente", "ventes", "commercial"],
            "marketing": ["mkt", "mktg"],
            "drh": ["directeur ressources humaines", "directrice ressources humaines", "hr director", "rh"],
            "dsi": ["directeur systemes information", "it director", "cio"],
            "daf": ["directeur administratif financier", "cfo", "finance director"],
            "pdg": ["president directeur general", "ceo", "chief executive"],
            "ceo": ["pdg", "president directeur general"],
            "cto": ["directeur technique", "chief technology officer"],
            "responsable": ["manager", "head", "chef", "resp"],
            "achats": ["purchasing", "procurement", "achat", "buyer", "sourcing"],
            "achat": ["purchasing", "procurement", "achats", "buyer", "sourcing"],
            "technique": ["technical", "tech", "engineering"],
            "general": ["generale", "général", "générale"],
            "ressources": ["resources", "rh", "hr"],
            "humaines": ["human", "hr", "rh"],
            "financier": ["finance", "financial", "cfo"],
            "informatique": ["it", "information", "systemes"],
            "operations": ["ops", "opérations"],
        }

        # Words to ignore (common but not distinctive)
        stopwords = {"de", "des", "du", "la", "le", "les", "et", "en", "au", "aux", "à"}

        # Extract significant words from job function (at least 3 chars, not stopwords)
        job_words = [w for w in job_lower.split() if len(w) >= 3 and w not in stopwords]

        if not job_words:
            return True  # If no significant words, accept all

        # ALL significant words must match (either directly or via synonym)
        for word in job_words:
            word_found = False

            # Direct match
            if word in combined_text:
                word_found = True
            else:
                # Check synonyms
                if word in job_synonyms:
                    for synonym in job_synonyms[word]:
                        if synonym in combined_text:
                            word_found = True
                            break

            # If this word was not found, the result doesn't match
            if not word_found:
                logger.debug(f"Job function word '{word}' not found in result")
                return False

        return True


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
