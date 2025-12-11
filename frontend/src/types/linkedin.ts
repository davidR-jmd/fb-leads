/**
 * LinkedIn module TypeScript types
 * Mirrors backend schemas for type safety (DRY - single source of truth)
 */

export enum LinkedInStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  NEED_EMAIL_CODE = 'need_email_code',
  NEED_MANUAL_LOGIN = 'need_manual_login',
  AWAITING_MANUAL_LOGIN = 'awaiting_manual_login',
  CONNECTED = 'connected',
  BUSY = 'busy',
  ERROR = 'error',
}

export enum LinkedInAuthMethod {
  COOKIE = 'cookie',
  CREDENTIALS = 'credentials',
  MANUAL = 'manual',
}

export interface LinkedInConnectRequest {
  email: string;
  password: string;
}

export interface LinkedInCookieConnectRequest {
  cookie: string;
}

export interface LinkedInVerifyCodeRequest {
  code: string;
}

export interface LinkedInSearchRequest {
  query: string;
  limit?: number; // Default 50, max 100
}

export interface LinkedInCompanySearchRequest {
  companies: string[]; // List of company names from Excel
  keywords?: string; // Additional search keywords (e.g., "Directeur Marketing")
  limit_per_company?: number; // Default 10
}

export interface LinkedInStatusResponse {
  status: LinkedInStatus;
  email?: string | null;
  last_connected?: string | null;
  error_message?: string | null;
  auth_method?: LinkedInAuthMethod | null;
}

export interface LinkedInConnectResponse {
  status: LinkedInStatus;
  message?: string | null;
}

export interface LinkedInContact {
  name?: string | null;
  title?: string | null;
  company?: string | null;
  location?: string | null;
  profile_url?: string | null;
}

export interface LinkedInSearchResponse {
  contacts: LinkedInContact[];
  query: string;
  total_found: number;
}

export interface LinkedInCompanySearchResponse {
  contacts: LinkedInContact[];
  companies_searched: number;
  total_found: number;
  keywords: string;
}

export interface SearchSessionResponse {
  session_id: string;
  status: string;
  total_companies: number;
  message: string;
}

export interface SearchResultsPageResponse {
  results: LinkedInContact[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  companies_searched: number;
  total_companies: number;
  status: string;
}

export interface SearchSessionStatusResponse {
  session_id: string;
  status: string;
  companies_searched: number;
  total_companies: number;
  total_results: number;
  keywords: string;
  created_at: string;
}
