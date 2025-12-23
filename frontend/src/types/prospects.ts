/**
 * Prospect Finder TypeScript types
 * Mirrors backend schemas for type safety
 */

// =============================================================================
// Enums
// =============================================================================

export enum SearchMode {
  MANUAL = 'manual',
  EXCEL_IMPORT = 'excel_import',
}

export enum SearchStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// =============================================================================
// Nested Types
// =============================================================================

export interface CompanyAddress {
  street?: string | null;
  postal_code?: string | null;
  city?: string | null;
}

export interface CompanyData {
  name: string;
  siren?: string | null;
  siret?: string | null;
  revenue?: number | null;
  employees?: number | null;
  employees_range?: string | null;
  address?: CompanyAddress | null;
  naf_code?: string | null;
  naf_label?: string | null;
  legal_form?: string | null;
  creation_date?: string | null;
}

export interface ContactData {
  name?: string | null;
  title?: string | null;
  linkedin_url?: string | null;
}

export interface SearchFilters {
  company_name?: string | null;
  departements?: string[] | null;
  size_min?: number | null;
  size_max?: number | null;
  revenue_min?: number | null;
  revenue_max?: number | null;
  industry_naf?: string | null;
  is_public?: boolean | null;
}

export interface SearchProgress {
  total_companies: number;
  processed: number;
  found: number;
  errors: number;
}

// =============================================================================
// Request Types
// =============================================================================

export interface SimpleSearchRequest {
  job_function: string;
  company_name: string;
}

export interface ProspectSearchRequest {
  job_function: string;
  filters?: SearchFilters | null;
}

export interface CompanyLookupRequest {
  query: string;
  by: 'name' | 'siren';
}

// =============================================================================
// Response Types
// =============================================================================

export interface ProspectResult {
  company: CompanyData;
  contact?: ContactData | null;
  searched_function: string;
  linkedin_found: boolean;
  source: string;
}

export interface SimpleSearchResponse {
  company: CompanyData;
  contacts: ContactData[];  // Multiple LinkedIn profiles
  searched_function: string;
  linkedin_found: boolean;
  profiles_count: number;  // Number of profiles found
}

export interface ProspectSearchResponse {
  job_id: string;
  status: SearchStatus;
  estimated_companies: number;
  message?: string | null;
}

export interface ProspectSearchResultsResponse {
  job_id: string;
  status: SearchStatus;
  progress: SearchProgress;
  results: ProspectResult[];
}

export interface CompanyLookupResponse {
  companies: CompanyData[];
}

// =============================================================================
// Utility Types
// =============================================================================

export interface DepartementOption {
  code: string;
  name: string;
}

// Common French departments
export const FRENCH_DEPARTEMENTS: DepartementOption[] = [
  { code: '75', name: 'Paris' },
  { code: '69', name: 'Rhone' },
  { code: '13', name: 'Bouches-du-Rhone' },
  { code: '31', name: 'Haute-Garonne' },
  { code: '33', name: 'Gironde' },
  { code: '59', name: 'Nord' },
  { code: '67', name: 'Bas-Rhin' },
  { code: '92', name: 'Hauts-de-Seine' },
  { code: '93', name: 'Seine-Saint-Denis' },
  { code: '94', name: 'Val-de-Marne' },
  { code: '44', name: 'Loire-Atlantique' },
  { code: '34', name: 'Herault' },
  { code: '06', name: 'Alpes-Maritimes' },
  { code: '78', name: 'Yvelines' },
  { code: '91', name: 'Essonne' },
];

// Common job functions
export const COMMON_JOB_FUNCTIONS = [
  'Directeur Commercial',
  'Directeur Marketing',
  'DRH',
  'DSI',
  'DAF',
  'PDG',
  'CEO',
  'Directeur General',
  'Directeur Technique',
  'CTO',
  'Responsable Achats',
  'Directeur des Operations',
];
