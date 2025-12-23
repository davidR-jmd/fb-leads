"""Prospect Finder service - orchestrates company lookup and contact finding."""

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.prospects.clients.pappers import PappersClient, get_pappers_client
from app.prospects.clients.google_search import GoogleSearchClient, get_google_search_client
from app.prospects.repository import ProspectRepository, get_prospect_repository
from app.prospects.schemas import (
    CompanyData,
    ContactData,
    SimpleSearchRequest,
    SimpleSearchResponse,
    ProspectSearchRequest,
    ProspectSearchResponse,
    ProspectResult,
    SearchStatus,
    SearchProgress,
)

logger = logging.getLogger(__name__)


class ProspectService:
    """Service for prospect finding operations."""

    def __init__(
        self,
        pappers_client: PappersClient,
        google_client: GoogleSearchClient,
        repository: ProspectRepository,
    ) -> None:
        """Initialize the prospect service.

        Args:
            pappers_client: Pappers API client
            google_client: Google Search API client
            repository: Database repository
        """
        self._pappers = pappers_client
        self._google = google_client
        self._repository = repository

    async def simple_search(self, request: SimpleSearchRequest) -> SimpleSearchResponse:
        """Execute the simplest search: function + company name.

        This is the V1 workflow:
        1. Look up company in Pappers
        2. Search for LinkedIn profile via Google
        3. Return combined result

        Args:
            request: Search request with job_function and company_name

        Returns:
            SimpleSearchResponse with company and contact data
        """
        logger.info(f"Simple search: {request.job_function} at {request.company_name}")

        # Step 1: Check cache first
        cached_company = await self._repository.get_cached_company_by_name(request.company_name)

        if cached_company:
            logger.info(f"Using cached company data for: {request.company_name}")
            company_data = self._cache_to_company_data(cached_company)
        else:
            # Step 2: Look up company in Pappers
            company_data = await self._pappers.search_by_name(request.company_name)

            if not company_data:
                # Company not found - create minimal data
                logger.warning(f"Company not found in Pappers: {request.company_name}")
                company_data = CompanyData(name=request.company_name)
            else:
                # Cache the company data
                if company_data.siren:
                    await self._repository.cache_company(
                        siren=company_data.siren,
                        name=company_data.name,
                        siret_siege=company_data.siret,
                        revenue=company_data.revenue,
                        employees=company_data.employees,
                        employees_range=company_data.employees_range,
                        address_street=company_data.address.street if company_data.address else None,
                        address_postal_code=company_data.address.postal_code if company_data.address else None,
                        address_city=company_data.address.city if company_data.address else None,
                        naf_code=company_data.naf_code,
                        naf_label=company_data.naf_label,
                        legal_form=company_data.legal_form,
                        creation_date=company_data.creation_date,
                    )

        # Step 3: Search for LinkedIn profiles (multiple)
        contacts = await self._google.find_linkedin_profile(
            job_function=request.job_function,
            company_name=company_data.name,
            max_results=10,
        )

        linkedin_found = len(contacts) > 0
        profiles_count = len(contacts)

        logger.info(f"Search complete: linkedin_found={linkedin_found}, profiles_count={profiles_count}")

        return SimpleSearchResponse(
            company=company_data,
            contacts=contacts,
            searched_function=request.job_function,
            linkedin_found=linkedin_found,
            profiles_count=profiles_count,
        )

    async def search_with_filters(
        self,
        user_id: str,
        request: ProspectSearchRequest,
    ) -> ProspectSearchResponse:
        """Start a search job with filters.

        This creates a job that can process multiple companies.

        Args:
            user_id: ID of the user making the request
            request: Search request with job_function and optional filters

        Returns:
            ProspectSearchResponse with job_id
        """
        logger.info(f"Starting filtered search for user {user_id}: {request.job_function}")

        # If a specific company is provided, do simple search
        if request.filters and request.filters.company_name:
            job_id = await self._repository.create_search_job(
                user_id=user_id,
                job_function=request.job_function,
                company_name=request.filters.company_name,
            )

            # Update progress
            await self._repository.update_job_progress(
                job_id=job_id,
                progress=SearchProgress(total_companies=1),
            )

            # Execute search immediately for single company
            simple_request = SimpleSearchRequest(
                job_function=request.job_function,
                company_name=request.filters.company_name,
            )
            result = await self.simple_search(simple_request)

            # Store result
            await self._repository.add_result_to_job(
                job_id=job_id,
                company_data=result.company,
                contacts=result.contacts,
                searched_function=request.job_function,
            )

            # Mark complete
            await self._repository.update_job_status(job_id, SearchStatus.COMPLETED)

            return ProspectSearchResponse(
                job_id=job_id,
                status=SearchStatus.COMPLETED,
                estimated_companies=1,
                message="Search completed",
            )

        # For filtered search without specific company, search Pappers
        filters = request.filters
        if filters:
            companies = await self._pappers.search_companies(
                departement=filters.departements,
                effectif_min=filters.size_min,
                effectif_max=filters.size_max,
                ca_min=filters.revenue_min,
                ca_max=filters.revenue_max,
                code_naf=filters.industry_naf,
            )

            if not companies:
                return ProspectSearchResponse(
                    job_id="",
                    status=SearchStatus.FAILED,
                    estimated_companies=0,
                    message="No companies found matching filters",
                )

            # Create job
            job_id = await self._repository.create_search_job(
                user_id=user_id,
                job_function=request.job_function,
                filters=filters.model_dump(exclude_none=True) if filters else None,
            )

            # Update progress
            await self._repository.update_job_progress(
                job_id=job_id,
                progress=SearchProgress(total_companies=len(companies)),
            )

            # Process companies (for now, synchronously - later can be async)
            await self._repository.update_job_status(job_id, SearchStatus.PROCESSING)

            for company in companies:
                try:
                    # Search for LinkedIn profiles (multiple)
                    contacts = await self._google.find_linkedin_profile(
                        job_function=request.job_function,
                        company_name=company.name,
                        max_results=10,
                    )

                    await self._repository.add_result_to_job(
                        job_id=job_id,
                        company_data=company,
                        contacts=contacts,
                        searched_function=request.job_function,
                    )

                except Exception as e:
                    logger.error(f"Error processing company {company.name}: {e}")
                    await self._repository.add_error_to_job(job_id, company.name)

            await self._repository.update_job_status(job_id, SearchStatus.COMPLETED)

            return ProspectSearchResponse(
                job_id=job_id,
                status=SearchStatus.COMPLETED,
                estimated_companies=len(companies),
                message=f"Processed {len(companies)} companies",
            )

        # No filters provided
        return ProspectSearchResponse(
            job_id="",
            status=SearchStatus.FAILED,
            estimated_companies=0,
            message="Please provide a company name or filters",
        )

    async def get_job_results(self, job_id: str) -> dict[str, Any] | None:
        """Get results for a search job.

        Args:
            job_id: Search job ID

        Returns:
            Job data with results, or None if not found
        """
        return await self._repository.get_search_job(job_id)

    def _cache_to_company_data(self, cached: dict[str, Any]) -> CompanyData:
        """Convert cached company document to CompanyData.

        Args:
            cached: Cached document from MongoDB

        Returns:
            CompanyData object
        """
        from app.prospects.schemas import CompanyAddress

        address = None
        if cached.get("address_street") or cached.get("address_city"):
            address = CompanyAddress(
                street=cached.get("address_street"),
                postal_code=cached.get("address_postal_code"),
                city=cached.get("address_city"),
            )

        return CompanyData(
            name=cached.get("name", ""),
            siren=cached.get("siren"),
            siret=cached.get("siret_siege"),
            revenue=cached.get("revenue"),
            employees=cached.get("employees"),
            employees_range=cached.get("employees_range"),
            address=address,
            naf_code=cached.get("naf_code"),
            naf_label=cached.get("naf_label"),
            legal_form=cached.get("legal_form"),
            creation_date=cached.get("creation_date"),
        )


# =============================================================================
# Singleton instance
# =============================================================================

_prospect_service: ProspectService | None = None


def get_prospect_service(db: AsyncIOMotorDatabase) -> ProspectService:
    """Get singleton prospect service instance.

    Args:
        db: MongoDB database instance

    Returns:
        ProspectService instance
    """
    global _prospect_service
    if _prospect_service is None:
        _prospect_service = ProspectService(
            pappers_client=get_pappers_client(),
            google_client=get_google_search_client(),
            repository=get_prospect_repository(db),
        )
    return _prospect_service
