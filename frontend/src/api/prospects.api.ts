/**
 * Prospects API service
 * Single Responsibility: Handle all Prospect Finder API calls
 */
import apiClient from './client';
import type {
  SimpleSearchRequest,
  SimpleSearchResponse,
  ProspectSearchRequest,
  ProspectSearchResponse,
  ProspectSearchResultsResponse,
  CompanyLookupRequest,
  CompanyLookupResponse,
} from '../types/prospects';

export const prospectsApi = {
  /**
   * Simple search: Find a contact by job function and company name
   * This is the primary V1 workflow
   */
  simpleSearch: async (data: SimpleSearchRequest): Promise<SimpleSearchResponse> => {
    const response = await apiClient.post<SimpleSearchResponse>('/prospects/simple-search', data);
    return response.data;
  },

  /**
   * Full search with filters
   * Creates a search job that can process multiple companies
   */
  search: async (data: ProspectSearchRequest): Promise<ProspectSearchResponse> => {
    const response = await apiClient.post<ProspectSearchResponse>('/prospects/search', data);
    return response.data;
  },

  /**
   * Get results for a search job
   */
  getSearchResults: async (jobId: string): Promise<ProspectSearchResultsResponse> => {
    const response = await apiClient.get<ProspectSearchResultsResponse>(`/prospects/search/${jobId}`);
    return response.data;
  },

  /**
   * Lookup a company by name or SIREN
   * Useful for autocomplete or validation
   */
  lookupCompany: async (data: CompanyLookupRequest): Promise<CompanyLookupResponse> => {
    const response = await apiClient.post<CompanyLookupResponse>('/prospects/company/lookup', data);
    return response.data;
  },
};
