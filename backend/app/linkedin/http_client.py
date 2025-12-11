"""LinkedIn HTTP client using cookies directly (no browser automation).

This approach is simpler and more reliable than browser automation:
- Uses httpx for async HTTP requests
- Injects li_at cookie directly into requests
- No browser fingerprinting issues
- Works in Docker without display
"""

import json
import logging
import re
from typing import Any
from urllib.parse import quote
import httpx
from bs4 import BeautifulSoup

from app.linkedin.schemas import LinkedInContact

logger = logging.getLogger(__name__)


class LinkedInHttpClient:
    """HTTP-based LinkedIn client using session cookies."""

    # LinkedIn API endpoints (used by their frontend)
    BASE_URL = "https://www.linkedin.com"
    VOYAGER_API = "https://www.linkedin.com/voyager/api"

    # Headers to mimic browser
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Li-Lang": "fr_FR",
        "X-RestLi-Protocol-Version": "2.0.0",
    }

    def __init__(self) -> None:
        """Initialize HTTP client."""
        self._li_at_cookie: str | None = None
        self._csrf_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with cookies."""
        if self._client is None or self._client.is_closed:
            cookies = {}
            if self._li_at_cookie:
                cookies["li_at"] = self._li_at_cookie
            if self._csrf_token:
                cookies["JSESSIONID"] = self._csrf_token

            self._client = httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                cookies=cookies,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def set_cookie(self, li_at_cookie: str) -> None:
        """Set the li_at session cookie."""
        self._li_at_cookie = li_at_cookie.strip()
        # Reset client to pick up new cookie
        if self._client:
            self._client = None
        logger.info(f"Cookie set (length={len(self._li_at_cookie)})")

    def has_cookie(self) -> bool:
        """Check if cookie is set."""
        return self._li_at_cookie is not None and len(self._li_at_cookie) > 0

    async def validate_session(self) -> bool:
        """Validate if the session cookie is valid by making a test request."""
        if not self.has_cookie():
            logger.warning("No cookie set")
            return False

        try:
            client = await self._get_client()

            # Try to access the feed - if redirected to login, session is invalid
            response = await client.get(
                f"{self.BASE_URL}/feed/",
                follow_redirects=False,  # Don't follow to see if redirected to login
            )

            logger.info(f"Session validation: status={response.status_code}, url={response.headers.get('location', 'N/A')}")

            # 200 = logged in, 302 to login = not logged in
            if response.status_code == 200:
                # Try to extract CSRF token from response
                await self._extract_csrf_token(response)
                return True

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location", "")
                if "login" in location.lower() or "authwall" in location.lower():
                    logger.warning("Session invalid - redirected to login")
                    return False
                # Might be a different redirect, try following
                return await self._follow_and_check(client)

            return False

        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False

    async def _follow_and_check(self, client: httpx.AsyncClient) -> bool:
        """Follow redirects and check if we end up logged in."""
        try:
            response = await client.get(f"{self.BASE_URL}/feed/")
            if response.status_code == 200 and "login" not in response.url.path.lower():
                await self._extract_csrf_token(response)
                return True
            return False
        except Exception:
            return False

    async def _extract_csrf_token(self, response: httpx.Response) -> None:
        """Extract CSRF token from response cookies or client cookies."""
        # First check response cookies
        for cookie_name, cookie_value in response.cookies.items():
            if cookie_name == "JSESSIONID":
                self._csrf_token = cookie_value.strip('"')
                logger.info(f"CSRF token from response: {self._csrf_token[:30]}...")
                return

        # Then check client cookies (might have been set during redirect)
        if self._client:
            jsession = self._client.cookies.get("JSESSIONID")
            if jsession:
                self._csrf_token = jsession.strip('"')
                logger.info(f"CSRF token from client: {self._csrf_token[:30]}...")
                return

        # Try to extract from HTML
        import re
        match = re.search(r'"csrfToken":"([^"]+)"', response.text)
        if match:
            self._csrf_token = match.group(1)
            logger.info(f"CSRF token from HTML: {self._csrf_token[:30]}...")
            return

        logger.warning("Could not extract CSRF token from any source")

    async def _get_company_id(self, company_name: str) -> str | None:
        """Search for a company and return its LinkedIn ID.

        Args:
            company_name: Name of the company to search for

        Returns:
            LinkedIn company ID (urn format) or None if not found
        """
        try:
            client = await self._get_client()
            headers = {**self.DEFAULT_HEADERS}
            if self._csrf_token:
                headers["Csrf-Token"] = self._csrf_token

            # Search for company using typeahead API
            search_url = (
                f"{self.VOYAGER_API}/typeahead/hitsV2"
                f"?keywords={quote(company_name)}"
                f"&origin=GLOBAL_SEARCH_HEADER"
                f"&q=type"
                f"&type=COMPANY"
            )

            response = await client.get(search_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                if elements:
                    # Get the first matching company
                    for element in elements:
                        target_urn = element.get("targetUrn", "")
                        if target_urn and "company" in target_urn.lower():
                            # Extract company ID from URN like "urn:li:company:12345"
                            company_id = target_urn.split(":")[-1]
                            logger.info(f"Found company ID for '{company_name}': {company_id}")
                            return company_id

            logger.warning(f"Could not find company ID for '{company_name}'")
            return None

        except Exception as e:
            logger.error(f"Error getting company ID: {e}")
            return None

    async def search_people(
        self,
        query: str,
        limit: int = 10,
        company_filter: str | None = None,
        keywords_filter: str | None = None,
    ) -> list[LinkedInContact]:
        """Search for people on LinkedIn using advanced filters.

        Args:
            query: Search query (e.g., "Marketing Director Paris")
            limit: Maximum number of results
            company_filter: If provided, filter by current company name
            keywords_filter: If provided, filter by job title keywords

        Returns:
            List of LinkedIn contacts
        """
        if not self.has_cookie():
            raise RuntimeError("No session cookie set")

        try:
            client = await self._get_client()

            # First, ensure we have a CSRF token by visiting a page
            if not self._csrf_token:
                logger.info("Fetching CSRF token...")
                response = await client.get(f"{self.BASE_URL}/feed/")
                logger.info(f"Feed response cookies: {list(response.cookies.keys())}")
                logger.info(f"Client cookies: {list(client.cookies.keys())}")
                await self._extract_csrf_token(response)

            if not self._csrf_token:
                logger.warning("Could not extract CSRF token - API calls will likely fail")

            headers = {
                "User-Agent": self.DEFAULT_HEADERS["User-Agent"],
                "Accept": "application/vnd.linkedin.normalized+json+2.1",
                "Accept-Language": "en-US,en;q=0.9",
                "X-Li-Lang": "en_US",
                "X-RestLi-Protocol-Version": "2.0.0",
                "X-Li-Track": '{"clientVersion":"1.13.0","mpVersion":"1.13.0","osName":"web","timezoneOffset":2,"timezone":"Europe/Paris","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":1,"displayWidth":1920,"displayHeight":1080}',
            }
            if self._csrf_token:
                headers["Csrf-Token"] = self._csrf_token

            # Build search query with filters
            search_query = query
            if company_filter and company_filter not in query:
                search_query = f"{query} {company_filter}".strip()

            # Try GraphQL endpoint first
            search_url = (
                f"{self.VOYAGER_API}/graphql"
                f"?variables=(start:0,origin:GLOBAL_SEARCH_HEADER,query:(keywords:{quote(search_query)},flagshipSearchIntent:SEARCH_SRP,queryParameters:List((key:resultType,value:List(PEOPLE))),includeFiltersInResponse:false))"
                f"&queryId=voyagerSearchDashClusters.2268f03bb249beb14d05fcf85fbf8b25"
            )

            logger.info(f"Voyager search: {search_url[:100]}...")
            response = await client.get(search_url, headers=headers)

            logger.info(f"Voyager response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                with open("/tmp/voyager_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("Saved Voyager response to /tmp/voyager_response.json")

                contacts = self._parse_voyager_graphql(data, limit * 3)
                if contacts:
                    # Post-filter results if filters are provided
                    if company_filter or keywords_filter:
                        contacts = self._filter_contacts(contacts, company_filter, keywords_filter)
                    if contacts:
                        return contacts[:limit]

            # If GraphQL fails, try the dash search clusters endpoint
            logger.info("Trying dash search endpoint...")
            search_url2 = (
                f"{self.VOYAGER_API}/search/dash/clusters"
                f"?decorationId=com.linkedin.voyager.dash.deco.search.SearchClusterCollection-175"
                f"&origin=GLOBAL_SEARCH_HEADER"
                f"&q=all"
                f"&query=(keywords:{quote(search_query)},flagshipSearchIntent:SEARCH_SRP,queryParameters:(resultType:List(PEOPLE)))"
                f"&start=0"
                f"&count={limit * 3}"
            )

            response = await client.get(search_url2, headers=headers)
            logger.info(f"Dash search response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                with open("/tmp/dash_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("Saved dash response to /tmp/dash_response.json")

                contacts = self._parse_dash_search(data, limit * 3)
                if contacts:
                    # Post-filter results if filters are provided
                    if company_filter or keywords_filter:
                        contacts = self._filter_contacts(contacts, company_filter, keywords_filter)
                    if contacts:
                        return contacts[:limit]

            # Final fallback: HTML scraping
            logger.warning("All API methods failed, falling back to HTML")
            contacts = await self._search_via_html(query, limit * 3, company_filter, keywords_filter)

            if company_filter or keywords_filter:
                contacts = self._filter_contacts(contacts, company_filter, keywords_filter)

            return contacts[:limit]

        except Exception as e:
            logger.error(f"Search error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_voyager_graphql(self, data: dict, limit: int) -> list[LinkedInContact]:
        """Parse Voyager GraphQL response."""
        contacts = []
        try:
            included = data.get("included", [])
            logger.info(f"GraphQL included items: {len(included)}")

            for item in included:
                # Look for profile data
                if item.get("$type") == "com.linkedin.voyager.dash.identity.profile.Profile":
                    first_name = item.get("firstName", "")
                    last_name = item.get("lastName", "")
                    name = f"{first_name} {last_name}".strip()

                    if not name:
                        continue

                    public_id = item.get("publicIdentifier")
                    profile_url = f"https://www.linkedin.com/in/{public_id}" if public_id else None

                    contacts.append(LinkedInContact(
                        name=name,
                        title=item.get("headline"),
                        location=None,
                        profile_url=profile_url,
                    ))

                    if len(contacts) >= limit:
                        break

            logger.info(f"Parsed {len(contacts)} contacts from GraphQL")
            return contacts

        except Exception as e:
            logger.error(f"Error parsing GraphQL: {e}")
            return []

    def _parse_dash_search(self, data: dict, limit: int) -> list[LinkedInContact]:
        """Parse dash search clusters response."""
        contacts = []
        try:
            included = data.get("included", [])
            logger.info(f"Dash included items: {len(included)}")

            # Look for EntityResultViewModel items - these contain the search results
            for item in included:
                item_type = item.get("$type", "")

                if item_type == "com.linkedin.voyager.dash.search.EntityResultViewModel":
                    # Extract name from title
                    title_obj = item.get("title", {})
                    name = title_obj.get("text", "") if isinstance(title_obj, dict) else ""

                    if not name or len(name) < 2:
                        continue

                    # Extract headline from primarySubtitle
                    subtitle_obj = item.get("primarySubtitle", {})
                    headline = subtitle_obj.get("text", "") if isinstance(subtitle_obj, dict) else None

                    # Extract location from secondarySubtitle
                    location_obj = item.get("secondarySubtitle", {})
                    location = location_obj.get("text", "") if isinstance(location_obj, dict) else None

                    # Get profile URL
                    profile_url = item.get("navigationUrl")

                    contacts.append(LinkedInContact(
                        name=name,
                        title=headline,
                        location=location,
                        profile_url=profile_url,
                    ))

                    if len(contacts) >= limit:
                        break

            # Dedupe
            seen = set()
            unique = []
            for c in contacts:
                key = c.profile_url or c.name
                if key not in seen:
                    seen.add(key)
                    unique.append(c)

            logger.info(f"Parsed {len(unique)} contacts from dash search")
            return unique

        except Exception as e:
            logger.error(f"Error parsing dash search: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _filter_contacts(
        self,
        contacts: list[LinkedInContact],
        company_filter: str | None,
        keywords_filter: str | None,
    ) -> list[LinkedInContact]:
        """Filter contacts to only include those matching the criteria.

        Args:
            contacts: List of contacts to filter
            company_filter: Company name to match (case insensitive, partial match)
            keywords_filter: Keywords to find in title (case insensitive)

        Returns:
            Filtered list of contacts
        """
        if not company_filter and not keywords_filter:
            return contacts

        filtered = []
        company_filter_lower = company_filter.lower().strip() if company_filter else None
        keywords_lower = [kw.lower().strip() for kw in keywords_filter.split() if kw.strip()] if keywords_filter else []

        for contact in contacts:
            # Check company match
            if company_filter_lower:
                contact_company = (contact.company or "").lower()
                contact_title = (contact.title or "").lower()

                # Company should be in the company field OR in the title (e.g., "Director at Company")
                company_match = (
                    company_filter_lower in contact_company or
                    company_filter_lower in contact_title or
                    # Also check for common patterns
                    any(word in contact_company for word in company_filter_lower.split()[:2])  # First 2 words
                )

                if not company_match:
                    logger.debug(f"Filtered out {contact.name}: company '{contact.company}' doesn't match '{company_filter}'")
                    continue

            # Check keywords match in title
            if keywords_lower:
                contact_title = (contact.title or "").lower()

                # At least one keyword should be in the title
                keywords_match = any(kw in contact_title for kw in keywords_lower)

                if not keywords_match:
                    logger.debug(f"Filtered out {contact.name}: title '{contact.title}' doesn't match keywords '{keywords_filter}'")
                    continue

            filtered.append(contact)

        logger.info(f"Filtered {len(contacts)} contacts to {len(filtered)} matching criteria")
        return filtered

    async def _search_via_html(
        self,
        query: str,
        limit: int,
        company_filter: str | None = None,
        keywords_filter: str | None = None,
    ) -> list[LinkedInContact]:
        """Search by fetching the search page and extracting CSRF, then using API."""
        # Build search query with filters
        search_query = query
        if company_filter and company_filter not in query:
            search_query = f"{query} {company_filter}".strip()

        contacts = []
        page = 1
        results_per_page = 10

        try:
            client = await self._get_client()

            # Use desktop browser headers to avoid mobile redirect
            html_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1",
                "Referer": f"{self.BASE_URL}/feed/",
            }

            while len(contacts) < limit and page <= 5:  # Max 5 pages to avoid too many requests
                # Build URL with pagination
                search_url = f"{self.BASE_URL}/search/results/people/?keywords={quote(search_query)}"
                if page > 1:
                    search_url += f"&page={page}"

                logger.info(f"Fetching page {page}: {search_url}")

                response = await client.get(search_url, headers=html_headers, follow_redirects=False)

                # Handle redirects manually to avoid mobile version
                if response.status_code in (301, 302, 307, 308):
                    location = response.headers.get("location", "")
                    logger.info(f"Redirect to: {location}")
                    # If redirecting to mobile, modify URL to stay on desktop
                    if "/m/" in location:
                        location = location.replace("/m/", "/")
                    response = await client.get(location, headers=html_headers)

                # Save HTML for debugging
                with open("/tmp/linkedin_search.html", "w") as f:
                    f.write(response.text)
                logger.info(f"Saved HTML to /tmp/linkedin_search.html ({len(response.text)} bytes)")

                page_contacts = self._parse_html_search_results(response.text, results_per_page * 2)

                if not page_contacts:
                    break  # No more results

                contacts.extend(page_contacts)
                page += 1

        except Exception as e:
            logger.error(f"Error parsing search API results: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for c in contacts:
            key = c.profile_url or c.name
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

    def _parse_search_page_html(self, html: str) -> list[LinkedInContact]:
        """Parse contacts directly from search results HTML."""
        contacts = []

        try:
            from bs4 import BeautifulSoup
            import re
            import json

            soup = BeautifulSoup(html, "lxml")

            # Find all script tags with embedded data
            for script in soup.find_all("script"):
                text = script.string
                if not text:
                    continue

                # Look for data that contains firstName/lastName
                if '"firstName"' in text and '"lastName"' in text and '"publicIdentifier"' in text:
                    # Try to find JSON objects in the script
                    # Look for patterns like {"firstName":"John","lastName":"Doe",...}
                    profile_pattern = r'\{[^{}]*"firstName"\s*:\s*"([^"]+)"[^{}]*"lastName"\s*:\s*"([^"]+)"[^{}]*(?:"publicIdentifier"\s*:\s*"([^"]+)")?[^{}]*\}'

                    for match in re.finditer(profile_pattern, text):
                        first_name = match.group(1)
                        last_name = match.group(2)
                        public_id = match.group(3) if match.lastindex >= 3 else None

                        if first_name and last_name:
                            name = f"{first_name} {last_name}"
                            if not self._is_invalid_name(name) and len(name) < 100:
                                profile_url = f"https://www.linkedin.com/in/{public_id}" if public_id else None
                                contacts.append(LinkedInContact(
                                    name=name,
                                    profile_url=profile_url,
                                ))

        except Exception as e:
            logger.error(f"Error parsing search page HTML: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for c in contacts:
            key = c.profile_url or c.name
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

    async def _search_connections(self, query: str, limit: int) -> list[LinkedInContact]:
        """Search user's connections which has more reliable data."""
        try:
            client = await self._get_client()
            headers = {**self.DEFAULT_HEADERS}
            if self._csrf_token:
                headers["Csrf-Token"] = self._csrf_token

            # Search in connections
            connections_url = (
                f"{self.VOYAGER_API}/relationships/dash/connections"
                f"?decorationId=com.linkedin.voyager.dash.deco.web.mynetwork.ConnectionListWithProfile-16"
                f"&count={limit}"
                f"&q=search"
                f"&sortType=RECENTLY_ADDED"
                f"&keywords={quote(query)}"
            )

            response = await client.get(connections_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return self._parse_connections_results(data)

            logger.warning(f"Connections API failed: {response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Connections search error: {e}")
            return []

    def _parse_connections_results(self, data: dict) -> list[LinkedInContact]:
        """Parse connections API results."""
        contacts = []

        try:
            # Check included array for profile data
            included = data.get("included", [])
            for item in included:
                item_type = item.get("$type", "")
                if "Profile" in item_type or "MiniProfile" in item_type:
                    first_name = item.get("firstName", "")
                    last_name = item.get("lastName", "")

                    if isinstance(first_name, str) and isinstance(last_name, str) and first_name and last_name:
                        name = f"{first_name} {last_name}"
                        if not self._is_invalid_name(name):
                            public_id = item.get("publicIdentifier", "")
                            profile_url = f"https://www.linkedin.com/in/{public_id}" if public_id else None
                            headline = item.get("headline", "") or item.get("occupation", "")

                            contacts.append(LinkedInContact(
                                name=name,
                                title=headline if headline else None,
                                profile_url=profile_url,
                            ))

        except Exception as e:
            logger.error(f"Error parsing connections results: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for c in contacts:
            key = c.profile_url or c.name
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

    def _parse_html_search_results(self, html: str, limit: int) -> list[LinkedInContact]:
        """Parse LinkedIn search results from HTML.

        LinkedIn renders search results as HTML elements with specific data-view-name attributes.
        """
        contacts = []

        try:
            soup = BeautifulSoup(html, "lxml")
            logger.info(f"HTML size: {len(html)} bytes")

            # Method 1: Parse HTML elements directly
            # Find all profile links with search-result-lockup-title
            title_links = soup.find_all("a", {"data-view-name": "search-result-lockup-title"})
            logger.info(f"Found {len(title_links)} search-result-lockup-title links")

            for link in title_links:
                try:
                    name = link.get_text(strip=True)
                    profile_url = link.get("href", "")

                    if not name or len(name) < 2:
                        continue

                    # Make sure URL is complete
                    if profile_url and not profile_url.startswith("http"):
                        profile_url = f"https://www.linkedin.com{profile_url}"

                    # Try to find headline/title - usually in a sibling or parent container
                    title = None
                    location = None

                    # Navigate up to find the container and look for other text
                    parent = link.find_parent()
                    for _ in range(5):  # Go up a few levels
                        if parent is None:
                            break
                        # Look for text that might be the headline
                        spans = parent.find_all("span")
                        for span in spans:
                            span_text = span.get_text(strip=True)
                            if span_text and span_text != name and len(span_text) > 5:
                                if title is None and len(span_text) < 200:
                                    # Skip common UI elements
                                    if not any(x in span_text.lower() for x in ["se connecter", "message", "suivre", "connexion"]):
                                        title = span_text
                                        break
                        if title:
                            break
                        parent = parent.find_parent()

                    contacts.append(LinkedInContact(
                        name=name,
                        title=title,
                        location=location,
                        profile_url=profile_url if profile_url else None,
                    ))

                except Exception as e:
                    logger.debug(f"Error extracting contact from link: {e}")
                    continue

            # Method 2: Extract from profile URLs in href attributes
            if not contacts:
                # Fallback: Find all LinkedIn profile links
                all_links = soup.find_all("a", href=re.compile(r"linkedin\.com/in/[^/]+"))
                logger.info(f"Fallback: Found {len(all_links)} profile links")

                seen_urls = set()
                for link in all_links:
                    href = link.get("href", "")
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    name = link.get_text(strip=True)
                    if name and len(name) >= 2 and len(name) < 100:
                        if not href.startswith("http"):
                            href = f"https://www.linkedin.com{href}"
                        contacts.append(LinkedInContact(
                            name=name,
                            title=None,
                            location=None,
                            profile_url=href,
                        ))

            # Deduplicate by profile URL or name
            seen = set()
            unique_contacts = []
            for contact in contacts:
                key = contact.profile_url or contact.name
                if key not in seen:
                    seen.add(key)
                    unique_contacts.append(contact)

            logger.info(f"Parsed {len(unique_contacts)} contacts from HTML (before dedup: {len(contacts)})")
            return unique_contacts[:limit]

        except Exception as e:
            logger.error(f"Error parsing HTML search results: {e}")
            return []

    def _extract_people_from_json(self, data: dict[str, Any]) -> list[LinkedInContact]:
        """Recursively extract people data from nested JSON structures."""
        contacts = []

        def recurse(obj: Any) -> None:
            if isinstance(obj, dict):
                # Check if this dict looks like a person
                if self._looks_like_person(obj):
                    contact = self._extract_contact_from_dict(obj)
                    if contact:
                        contacts.append(contact)
                # Recurse into nested dicts
                for value in obj.values():
                    recurse(value)
            elif isinstance(obj, list):
                for item in obj:
                    recurse(item)

        recurse(data)
        return contacts

    def _looks_like_person(self, obj: dict[str, Any]) -> bool:
        """Check if a dict looks like person data."""
        # Common patterns in LinkedIn data
        person_keys = {"firstName", "lastName", "fullName", "name", "title", "headline"}
        profile_keys = {"publicIdentifier", "profileUrl", "vanityName"}

        has_name = bool(person_keys & set(obj.keys()))
        has_profile = bool(profile_keys & set(obj.keys()))

        return has_name or has_profile

    def _extract_contact_from_dict(self, obj: dict[str, Any]) -> LinkedInContact | None:
        """Extract a LinkedInContact from a dict."""
        try:
            # Try different name formats
            name = (
                obj.get("fullName")
                or obj.get("name")
                or f"{obj.get('firstName', '')} {obj.get('lastName', '')}".strip()
            )

            if not name or len(name) < 2:
                return None

            # Get title/headline
            title = obj.get("headline") or obj.get("title") or obj.get("occupation")

            # Get location
            location = obj.get("location") or obj.get("locationName")
            if isinstance(location, dict):
                location = location.get("name") or location.get("default")

            # Get profile URL
            profile_url = obj.get("profileUrl") or obj.get("url")
            if not profile_url:
                public_id = obj.get("publicIdentifier") or obj.get("vanityName")
                if public_id:
                    profile_url = f"https://www.linkedin.com/in/{public_id}"

            return LinkedInContact(
                name=name,
                title=title if isinstance(title, str) else None,
                location=location if isinstance(location, str) else None,
                profile_url=profile_url if isinstance(profile_url, str) else None,
            )

        except Exception:
            return None

    def _parse_search_results(self, data: dict[str, Any]) -> list[LinkedInContact]:
        """Parse LinkedIn API search results."""
        contacts = []

        try:
            # LinkedIn's response structure is complex and nested
            elements = data.get("data", {}).get("elements", [])

            for element in elements:
                # Extract person data from the nested structure
                entity = element.get("entity", {})
                if not entity:
                    continue

                # Different structure for different result types
                title_data = entity.get("title", {})
                subtitle_data = entity.get("primarySubtitle", {})
                secondary_data = entity.get("secondarySubtitle", {})

                name = title_data.get("text", "") if isinstance(title_data, dict) else str(title_data)
                title = subtitle_data.get("text", "") if isinstance(subtitle_data, dict) else str(subtitle_data)
                location = secondary_data.get("text", "") if isinstance(secondary_data, dict) else str(secondary_data)

                # Get profile URL
                navigation = entity.get("navigationContext", {})
                profile_url = navigation.get("url", "")

                if name:
                    contacts.append(LinkedInContact(
                        name=name,
                        title=title or None,
                        location=location or None,
                        profile_url=profile_url or None,
                    ))

        except Exception as e:
            logger.error(f"Error parsing search results: {e}")

        logger.info(f"Parsed {len(contacts)} contacts from search results")
        return contacts


# Singleton instance
_http_client: LinkedInHttpClient | None = None


def get_linkedin_http_client() -> LinkedInHttpClient:
    """Get singleton HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = LinkedInHttpClient()
    return _http_client
