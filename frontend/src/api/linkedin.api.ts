/**
 * LinkedIn API service
 * Single Responsibility: Handle all LinkedIn API calls
 */
import apiClient from './client';
import type {
  LinkedInStatusResponse,
  LinkedInConnectRequest,
  LinkedInCookieConnectRequest,
  LinkedInConnectResponse,
  LinkedInVerifyCodeRequest,
  LinkedInSearchRequest,
  LinkedInSearchResponse,
} from '../types/linkedin';

export const linkedInApi = {
  /**
   * Get current LinkedIn connection status
   */
  getStatus: async (): Promise<LinkedInStatusResponse> => {
    const response = await apiClient.get<LinkedInStatusResponse>('/linkedin/status');
    return response.data;
  },

  /**
   * Connect to LinkedIn with credentials (admin only)
   * @deprecated Use connectWithCookie or openBrowserForManualLogin instead
   */
  connect: async (data: LinkedInConnectRequest): Promise<LinkedInConnectResponse> => {
    const response = await apiClient.post<LinkedInConnectResponse>('/linkedin/connect', data);
    return response.data;
  },

  /**
   * Connect to LinkedIn using li_at session cookie (admin only)
   * This is the primary recommended method - bypasses all login challenges
   */
  connectWithCookie: async (data: LinkedInCookieConnectRequest): Promise<LinkedInConnectResponse> => {
    const response = await apiClient.post<LinkedInConnectResponse>('/linkedin/connect-cookie', data);
    return response.data;
  },

  /**
   * Open visible browser for manual login (admin only)
   * Use as fallback when cookie auth fails or expires
   */
  openBrowserForManualLogin: async (): Promise<LinkedInConnectResponse> => {
    const response = await apiClient.post<LinkedInConnectResponse>('/linkedin/open-browser');
    return response.data;
  },

  /**
   * Submit email verification code (admin only)
   */
  verifyCode: async (data: LinkedInVerifyCodeRequest): Promise<LinkedInConnectResponse> => {
    const response = await apiClient.post<LinkedInConnectResponse>('/linkedin/verify-code', data);
    return response.data;
  },

  /**
   * Search for contacts on LinkedIn
   */
  search: async (data: LinkedInSearchRequest): Promise<LinkedInSearchResponse> => {
    const response = await apiClient.post<LinkedInSearchResponse>('/linkedin/search', data);
    return response.data;
  },

  /**
   * Disconnect from LinkedIn (admin only)
   */
  disconnect: async (): Promise<void> => {
    await apiClient.post('/linkedin/disconnect');
  },

  /**
   * Close browser instance (admin only)
   * Use to reset stuck browser
   */
  closeBrowser: async (): Promise<void> => {
    await apiClient.post('/linkedin/close-browser');
  },

  /**
   * Validate existing browser session (admin only)
   * Use after manually logging in via the browser window
   */
  validateSession: async (): Promise<LinkedInConnectResponse> => {
    const response = await apiClient.post<LinkedInConnectResponse>('/linkedin/validate-session');
    return response.data;
  },
};
