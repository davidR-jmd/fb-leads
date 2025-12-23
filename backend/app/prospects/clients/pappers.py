"""Pappers API client for French company data.

Pappers API documentation: https://www.pappers.fr/api/documentation
"""

import logging
from typing import Any

import httpx

from app.config import get_settings
from app.prospects.schemas import CompanyData, CompanyAddress

logger = logging.getLogger(__name__)


class PappersClient:
    """Client for Pappers API (French company data)."""

    BASE_URL = "https://api.pappers.fr/v2"

    def __init__(self, api_key: str) -> None:
        """Initialize Pappers client.

        Args:
            api_key: Pappers API key
        """
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
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

    async def search_by_name(self, company_name: str) -> CompanyData | None:
        """Search for a company by name.

        Args:
            company_name: Company name to search for

        Returns:
            CompanyData if found, None otherwise
        """
        if not self._api_key:
            logger.error("Pappers API key not configured")
            return None

        try:
            client = await self._get_client()

            response = await client.get(
                "/recherche",
                params={
                    "api_token": self._api_key,
                    "q": company_name,
                    "par_page": 1,  # We only need the first result
                },
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("resultats", [])

                if results:
                    return self._parse_company(results[0])

                logger.info(f"No company found for: {company_name}")
                return None

            elif response.status_code == 401:
                logger.error("Pappers API: Invalid API key")
                return None

            elif response.status_code == 429:
                logger.warning("Pappers API: Rate limit exceeded")
                return None

            else:
                logger.error(f"Pappers API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Pappers API request failed: {e}")
            return None

    async def get_by_siren(self, siren: str) -> CompanyData | None:
        """Get company by SIREN number.

        Args:
            siren: 9-digit SIREN number

        Returns:
            CompanyData if found, None otherwise
        """
        if not self._api_key:
            logger.error("Pappers API key not configured")
            return None

        try:
            client = await self._get_client()

            response = await client.get(
                "/entreprise",
                params={
                    "api_token": self._api_key,
                    "siren": siren,
                },
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_company(data)

            elif response.status_code == 404:
                logger.info(f"No company found for SIREN: {siren}")
                return None

            elif response.status_code == 401:
                logger.error("Pappers API: Invalid API key")
                return None

            else:
                logger.error(f"Pappers API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Pappers API request failed: {e}")
            return None

    async def search_companies(
        self,
        departement: list[str] | None = None,
        effectif_min: int | None = None,
        effectif_max: int | None = None,
        ca_min: int | None = None,
        ca_max: int | None = None,
        code_naf: str | None = None,
        forme_juridique: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> list[CompanyData]:
        """Search companies with filters.

        Args:
            departement: List of department codes (e.g., ["69", "75"])
            effectif_min: Minimum employee count
            effectif_max: Maximum employee count
            ca_min: Minimum revenue (chiffre d'affaires) in euros
            ca_max: Maximum revenue in euros
            code_naf: NAF/APE industry code
            forme_juridique: Legal form (SAS, SARL, SA, etc.)
            page: Page number (1-indexed)
            per_page: Results per page (max 100)

        Returns:
            List of CompanyData
        """
        if not self._api_key:
            logger.error("Pappers API key not configured")
            return []

        try:
            client = await self._get_client()

            # Build params
            params: dict[str, Any] = {
                "api_token": self._api_key,
                "page": page,
                "par_page": min(per_page, 100),
            }

            if departement:
                params["departement"] = ",".join(departement)

            if effectif_min is not None:
                params["effectif_min"] = effectif_min

            if effectif_max is not None:
                params["effectif_max"] = effectif_max

            if ca_min is not None:
                params["chiffre_affaires_min"] = ca_min

            if ca_max is not None:
                params["chiffre_affaires_max"] = ca_max

            if code_naf:
                params["code_naf"] = code_naf

            if forme_juridique:
                params["forme_juridique"] = forme_juridique

            response = await client.get("/recherche", params=params)

            if response.status_code == 200:
                data = response.json()
                results = data.get("resultats", [])
                return [self._parse_company(r) for r in results]

            else:
                logger.error(f"Pappers search error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Pappers search failed: {e}")
            return []

    def _parse_company(self, data: dict[str, Any]) -> CompanyData:
        """Parse Pappers API response into CompanyData.

        Args:
            data: Raw API response dict

        Returns:
            CompanyData object
        """
        # Parse address from siege data
        siege = data.get("siege", {})
        address = None
        if siege:
            address = CompanyAddress(
                street=siege.get("adresse_ligne_1"),
                postal_code=siege.get("code_postal"),
                city=siege.get("ville"),
            )

        # Parse employee count
        employees = None
        employees_range = data.get("effectif")
        if employees_range:
            # Try to extract a number from ranges like "50 a 99 salaries"
            try:
                if isinstance(employees_range, int):
                    employees = employees_range
                elif isinstance(employees_range, str):
                    # Extract first number from range
                    import re
                    match = re.search(r"(\d+)", employees_range)
                    if match:
                        employees = int(match.group(1))
            except (ValueError, TypeError):
                pass

        return CompanyData(
            name=data.get("nom_entreprise", data.get("denomination", "")),
            siren=data.get("siren"),
            siret=siege.get("siret") if siege else None,
            revenue=data.get("chiffre_affaires"),
            employees=employees,
            employees_range=employees_range if isinstance(employees_range, str) else None,
            address=address,
            naf_code=data.get("code_naf"),
            naf_label=data.get("libelle_code_naf"),
            legal_form=data.get("forme_juridique"),
            creation_date=data.get("date_creation"),
        )


# =============================================================================
# Singleton instance
# =============================================================================

_pappers_client: PappersClient | None = None


def get_pappers_client() -> PappersClient:
    """Get singleton Pappers client instance."""
    global _pappers_client
    if _pappers_client is None:
        settings = get_settings()
        _pappers_client = PappersClient(api_key=settings.pappers_api_key)
    return _pappers_client
