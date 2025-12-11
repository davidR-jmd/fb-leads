import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowLeft, AlertCircle, Search, ExternalLink, Loader2, Linkedin, ChevronLeft, ChevronRight, RefreshCw, Activity } from 'lucide-react';
import * as XLSX from 'xlsx';
import { TRANSLATIONS } from '../constants/translations';
import Stepper from '../components/Stepper';
import FileUploadZone from '../components/FileUploadZone';
import SelectDropdown from '../components/SelectDropdown';
import { linkedInApi } from '../api/linkedin.api';
import type { LinkedInContact, LinkedInStatusResponse, SearchResultsPageResponse, RateLimitStatus } from '../types/linkedin';
import { LinkedInStatus } from '../types/linkedin';

const t = TRANSLATIONS.pages.newSearch;

const STEPS = [
  { number: 1, label: t.steps.import },
  { number: 2, label: t.steps.validation },
  { number: 3, label: t.steps.synchronisation },
];

const PROFILE_OPTIONS = [
  { value: 'marketing_director', label: t.profiles.marketingDirector },
  { value: 'sales_director', label: t.profiles.salesDirector },
  { value: 'ceo', label: t.profiles.ceo },
  { value: 'cto', label: t.profiles.cto },
  { value: 'hr', label: t.profiles.hr },
];

export default function NouvelleRecherche() {
  const [currentStep, setCurrentStep] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [columnMapping, setColumnMapping] = useState({
    companyName: '',
    website: '',
  });
  const [profile, setProfile] = useState('marketing_director');
  const [columns, setColumns] = useState<string[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [companies, setCompanies] = useState<string[]>([]);
  const [keywords, setKeywords] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<LinkedInContact[]>([]);
  const [companiesSearched, setCompaniesSearched] = useState(0);
  const [totalCompanies, setTotalCompanies] = useState(0);
  const [linkedInStatus, setLinkedInStatus] = useState<LinkedInStatusResponse | null>(null);
  const [rateLimitData, setRateLimitData] = useState<RateLimitStatus | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);

  // Session and pagination state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [searchStatus, setSearchStatus] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [isCached, setIsCached] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const PAGE_SIZE = 20;

  // Load LinkedIn status on mount
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await linkedInApi.getStatus();
        setLinkedInStatus(status);

        // Load rate limit status if connected
        if (status.status === LinkedInStatus.CONNECTED) {
          try {
            const rateLimit = await linkedInApi.getRateLimitStatus();
            setRateLimitData(rateLimit);
          } catch (err) {
            console.error('Failed to load rate limit status:', err);
          }
        }
      } catch (err) {
        console.error('Failed to load LinkedIn status:', err);
      } finally {
        setIsLoadingStatus(false);
      }
    };
    loadStatus();
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Poll for search status and results
  const pollSearchStatus = useCallback(async (sessId: string) => {
    try {
      const status = await linkedInApi.getSearchSessionStatus(sessId);
      setSearchStatus(status.status);
      setCompaniesSearched(status.companies_searched);
      setTotalCompanies(status.total_companies);
      setTotalResults(status.total_results);

      // Always load page 1 during search to show new results as they come
      // This ensures users see results progressively
      if (status.total_results > 0) {
        const results = await linkedInApi.getSearchSessionResults(sessId, 1, PAGE_SIZE);
        setSearchResults(results.results);
        setTotalPages(results.total_pages);
        setCurrentPage(1);
      }

      // Stop polling when completed
      if (status.status === 'completed' || status.status === 'failed') {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setIsSearching(false);
        setCurrentStep(3);

        if (status.status === 'failed') {
          setSearchError('La recherche a échoué. Veuillez réessayer.');
        }
      }
    } catch (err) {
      console.error('Error polling search status:', err);
    }
  }, []);

  // Load page results
  const loadPageResults = useCallback(async (page: number) => {
    if (!sessionId) return;

    try {
      const results = await linkedInApi.getSearchSessionResults(sessionId, page, PAGE_SIZE);
      setSearchResults(results.results);
      setTotalPages(results.total_pages);
      setTotalResults(results.total);
      setCurrentPage(page);
    } catch (err) {
      console.error('Error loading page results:', err);
    }
  }, [sessionId]);

  const findEntrepriseColumn = (headers: string[]): string | null => {
    // Look for entreprise/enterprise column (case insensitive)
    const entrepriseVariants = ['entreprise', 'enterprise', 'company', 'société', 'societe'];
    for (const header of headers) {
      const normalizedHeader = header.toLowerCase().trim();
      if (entrepriseVariants.some(variant => normalizedHeader.includes(variant))) {
        return header;
      }
    }
    return null;
  };

  const handleFileSelect = async (selectedFile: File) => {
    setFileError(null);

    const isExcel = selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls');

    if (isExcel) {
      // Parse Excel file using xlsx library
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = e.target?.result;
          const workbook = XLSX.read(data, { type: 'array' });
          const sheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[sheetName];

          // Convert to JSON to find all possible header rows
          const jsonData = XLSX.utils.sheet_to_json<string[]>(worksheet, { header: 1 });

          // Find the row that contains "Enterprise" or "Entreprise" column
          let headerRowIndex = -1;
          let headers: string[] = [];
          let entrepriseColIndex = -1;

          for (let i = 0; i < Math.min(jsonData.length, 10); i++) {
            const row = jsonData[i];
            if (Array.isArray(row)) {
              // Keep original indices - don't filter
              const rowHeaders = row.map(cell => String(cell || '').trim());

              // Find the entreprise column with its original index
              // Must be an exact match or start with the variant (e.g., "Enterprise" or "Entreprise")
              for (let colIdx = 0; colIdx < rowHeaders.length; colIdx++) {
                const header = rowHeaders[colIdx];
                if (header) {
                  const normalizedHeader = header.toLowerCase().trim();
                  // Exact matches for column headers
                  const exactMatches = ['entreprise', 'enterprise', 'company', 'société', 'societe', 'nom entreprise', 'nom de l\'entreprise'];
                  if (exactMatches.includes(normalizedHeader) ||
                      normalizedHeader === 'enterprise' ||
                      normalizedHeader === 'entreprise') {
                    headerRowIndex = i;
                    headers = rowHeaders.filter(Boolean); // Filter for display only
                    entrepriseColIndex = colIdx; // Keep original index
                    break;
                  }
                }
              }
              if (headerRowIndex !== -1) break;
            }
          }

          if (headerRowIndex === -1 || entrepriseColIndex === -1) {
            setFileError("Le fichier Excel ne contient pas de colonne 'Entreprise'. Veuillez vérifier que votre fichier contient une colonne nommée 'Entreprise' ou 'Enterprise'.");
            setFile(null);
            setColumns([]);
            setCompanies([]);
            return;
          }

          setFile(selectedFile);
          setColumns(headers);

          // Auto-select the entreprise column for company name mapping
          const entrepriseCol = findEntrepriseColumn(headers);
          if (entrepriseCol) {
            setColumnMapping(prev => ({ ...prev, companyName: entrepriseCol }));
          }

          // Extract company names from the data rows using the correct column index
          const companyList: string[] = [];
          for (let i = headerRowIndex + 1; i < jsonData.length; i++) {
            const row = jsonData[i];
            if (Array.isArray(row) && row[entrepriseColIndex]) {
              const companyName = String(row[entrepriseColIndex]).trim();
              if (companyName && !companyList.includes(companyName)) {
                companyList.push(companyName);
              }
            }
          }
          setCompanies(companyList);
        } catch (error) {
          setFileError("Erreur lors de la lecture du fichier Excel. Veuillez vérifier que le fichier est valide.");
          setFile(null);
          setColumns([]);
        }
      };
      reader.readAsArrayBuffer(selectedFile);
    } else {
      // Parse CSV file
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        if (text) {
          const firstLine = text.split('\n')[0];
          const headers = firstLine.split(/[,;\t]/).map((h) => h.trim().replace(/"/g, ''));

          // Check for entreprise column in CSV
          const entrepriseCol = findEntrepriseColumn(headers);
          if (!entrepriseCol) {
            setFileError("Le fichier CSV ne contient pas de colonne 'Entreprise'. Veuillez vérifier que votre fichier contient une colonne nommée 'Entreprise' ou 'Enterprise'.");
            setFile(null);
            setColumns([]);
            return;
          }

          setFile(selectedFile);
          setColumns(headers);

          // Auto-select the entreprise column
          setColumnMapping(prev => ({ ...prev, companyName: entrepriseCol }));
        }
      };
      reader.readAsText(selectedFile);
    }
  };

  const handleLaunchSearch = async () => {
    if (companies.length === 0) {
      setSearchError("Aucune entreprise trouvée dans le fichier.");
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setCurrentPage(1);
    setIsCached(false);
    setCurrentStep(2);

    try {
      // Start streaming search
      const response = await linkedInApi.startSearchStream({
        companies,
        keywords: keywords.trim(),
        limit_per_company: 10,
      });

      setSessionId(response.session_id);
      setSearchStatus(response.status);
      setTotalCompanies(response.total_companies);

      // Check if results are cached
      if (response.status === 'completed') {
        setIsCached(true);
        setIsSearching(false);
        setCurrentStep(3);
        // Load cached results
        const results = await linkedInApi.getSearchSessionResults(response.session_id, 1, PAGE_SIZE);
        setSearchResults(results.results);
        setTotalPages(results.total_pages);
        setTotalResults(results.total);
        setCompaniesSearched(results.companies_searched);
      } else {
        // Start polling for results
        pollSearchStatus(response.session_id);
        pollingIntervalRef.current = setInterval(() => {
          pollSearchStatus(response.session_id);
        }, 2000); // Poll every 2 seconds
      }
    } catch (err: any) {
      setSearchError(err.response?.data?.detail || "Erreur lors de la recherche LinkedIn");
      setCurrentStep(1);
      setIsSearching(false);
    }
  };

  const columnOptions = columns.map((col) => ({ value: col, label: col }));

  return (
    <div>
      {/* Page Title */}
      <h1 className="text-2xl font-semibold text-slate-800 mb-6">{t.title}</h1>

      {/* LinkedIn Status Banner */}
      <div className={`rounded-lg border p-4 mb-6 ${
        isLoadingStatus
          ? 'bg-slate-50 border-slate-200'
          : linkedInStatus?.status === LinkedInStatus.CONNECTED
            ? 'bg-green-50 border-green-200'
            : linkedInStatus?.status === LinkedInStatus.BUSY
              ? 'bg-blue-50 border-blue-200'
              : 'bg-yellow-50 border-yellow-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Linkedin className={`${
              linkedInStatus?.status === LinkedInStatus.CONNECTED
                ? 'text-green-600'
                : linkedInStatus?.status === LinkedInStatus.BUSY
                  ? 'text-blue-600'
                  : 'text-yellow-600'
            }`} size={24} />
            <div>
              <p className={`font-medium ${
                linkedInStatus?.status === LinkedInStatus.CONNECTED
                  ? 'text-green-800'
                  : linkedInStatus?.status === LinkedInStatus.BUSY
                    ? 'text-blue-800'
                    : 'text-yellow-800'
              }`}>
                {isLoadingStatus
                  ? 'Chargement du statut LinkedIn...'
                  : linkedInStatus?.status === LinkedInStatus.CONNECTED
                    ? 'LinkedIn connecté'
                    : linkedInStatus?.status === LinkedInStatus.BUSY
                      ? 'LinkedIn occupé'
                      : 'LinkedIn non connecté'}
              </p>
              {linkedInStatus?.email && (
                <p className="text-sm text-slate-600">{linkedInStatus.email}</p>
              )}
            </div>
          </div>
          <div className={`w-3 h-3 rounded-full ${
            linkedInStatus?.status === LinkedInStatus.CONNECTED
              ? 'bg-green-500'
              : linkedInStatus?.status === LinkedInStatus.BUSY
                ? 'bg-blue-500 animate-pulse'
                : 'bg-yellow-500'
          }`} />
        </div>

        {/* Rate Limit Info - Show when connected */}
        {linkedInStatus?.status === LinkedInStatus.CONNECTED && rateLimitData && (
          <div className="mt-3 pt-3 border-t border-green-200">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <div className="flex items-center gap-2 text-green-700">
                <Activity size={16} />
                <span className="font-medium">Quotas :</span>
              </div>
              <div className={`${rateLimitData.searches_remaining_hour <= 5 ? 'text-amber-700 font-medium' : 'text-green-700'}`}>
                {rateLimitData.searches_remaining_hour}/{rateLimitData.limits.per_hour} cette heure
              </div>
              <span className="text-green-300">|</span>
              <div className={`${rateLimitData.searches_remaining_today <= 10 ? 'text-amber-700 font-medium' : 'text-green-700'}`}>
                {rateLimitData.searches_remaining_today}/{rateLimitData.limits.per_day} aujourd'hui
              </div>
              {rateLimitData.cooldown_remaining_minutes > 0 && (
                <>
                  <span className="text-green-300">|</span>
                  <div className="text-amber-700 font-medium flex items-center gap-1">
                    <AlertCircle size={14} />
                    Pause: {rateLimitData.cooldown_remaining_minutes} min
                  </div>
                </>
              )}
            </div>
            {/* Warning if near limits */}
            {(rateLimitData.searches_remaining_hour <= 5 || rateLimitData.searches_remaining_today <= 10) && (
              <p className="mt-2 text-xs text-amber-700">
                Vous approchez de la limite de recherches. Les recherches seront automatiquement espacées pour éviter le blocage.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Warning if not connected */}
      {!isLoadingStatus && linkedInStatus?.status !== LinkedInStatus.CONNECTED && linkedInStatus?.status !== LinkedInStatus.BUSY && (
        <div className="flex items-start gap-3 p-4 mb-6 bg-yellow-50 border border-yellow-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-800">LinkedIn non connecté</p>
            <p className="text-sm text-yellow-700 mt-1">
              Connectez-vous à LinkedIn dans les paramètres pour pouvoir effectuer des recherches.
            </p>
          </div>
        </div>
      )}

      {/* Stepper */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <Stepper steps={STEPS} currentStep={currentStep} />
      </div>

      {/* Back Button */}
      <button
        onClick={() => currentStep > 1 && setCurrentStep(currentStep - 1)}
        className="flex items-center gap-2 text-teal-600 hover:text-teal-700 mb-6 text-sm font-medium"
      >
        <ArrowLeft size={16} />
        {t.back}
      </button>

      {/* Main Content Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        {/* File Upload Zone */}
        <FileUploadZone
          onFileSelect={handleFileSelect}
          label={t.dropzone}
          className="mb-4"
        />

        {/* Error Message */}
        {fileError && (
          <div className="flex items-start gap-3 p-4 mb-8 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{fileError}</p>
          </div>
        )}

        {!fileError && <div className="mb-4" />}

        {/* Column Mapping Section */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-4">
            {t.columnMapping}
          </h3>
          <div className="max-w-md">
            <SelectDropdown
              options={columnOptions}
              value={columnMapping.companyName}
              onChange={(value) =>
                setColumnMapping((prev) => ({ ...prev, companyName: value }))
              }
              placeholder={t.companyName}
            />
          </div>
        </div>

        {/* Keywords Input */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-4">
            Mots-clés de recherche LinkedIn
          </h3>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="Ex: Directeur Marketing, CEO, Commercial..."
              className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isSearching}
            />
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Ces mots-clés seront combinés avec chaque entreprise pour la recherche LinkedIn
          </p>
        </div>

        {/* Companies List */}
        {companies.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-slate-700">
                Entreprises importées ({companies.length})
              </h3>
            </div>
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg max-h-48 overflow-y-auto">
              <div className="flex flex-wrap gap-2">
                {companies.map((company, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-white border border-blue-300 text-blue-800"
                  >
                    {company}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Search Error */}
        {searchError && (
          <div className="flex items-start gap-3 p-4 mb-6 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{searchError}</p>
          </div>
        )}

        {/* Launch Button */}
        {(() => {
          const isLinkedInReady = linkedInStatus?.status === LinkedInStatus.CONNECTED || linkedInStatus?.status === LinkedInStatus.BUSY;
          const isDisabled = !file || companies.length === 0 || isSearching || !isLinkedInReady;

          return (
            <button
              onClick={handleLaunchSearch}
              disabled={isDisabled}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-lg font-medium hover:from-blue-700 hover:to-blue-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSearching ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  Recherche en cours... ({companiesSearched}/{totalCompanies} entreprises)
                </>
              ) : !isLinkedInReady ? (
                <>
                  <AlertCircle size={20} />
                  LinkedIn non connecté
                </>
              ) : (
                <>
                  <Search size={20} />
                  Lancer la recherche LinkedIn
                </>
              )}
            </button>
          );
        })()}

        {/* Search Progress */}
        {isSearching && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-800">
                Recherche en cours...
              </span>
              <span className="text-sm text-blue-600">
                {companiesSearched}/{totalCompanies} entreprises
              </span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${totalCompanies > 0 ? (companiesSearched / totalCompanies) * 100 : 0}%` }}
              />
            </div>
            {totalResults > 0 && (
              <p className="text-sm text-blue-700 mt-2">
                {totalResults} contacts trouvés jusqu'à présent
              </p>
            )}
          </div>
        )}

        {/* Cached Results Notice */}
        {isCached && searchResults.length > 0 && (
          <div className="mt-4 flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-3">
            <RefreshCw size={16} />
            Résultats en cache (recherche effectuée précédemment)
          </div>
        )}

        {/* Results Section */}
        {searchResults.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                Résultats ({totalResults} contacts trouvés sur {companiesSearched} entreprises)
                {isSearching && (
                  <span className="inline-flex items-center gap-1 text-sm font-normal text-blue-600">
                    <Loader2 className="animate-spin" size={14} />
                    En cours...
                  </span>
                )}
              </h3>
            </div>

            {/* Results List - LinkedIn Style */}
            <div className="space-y-3">
              {searchResults.map((contact, index) => (
                <a
                  key={index}
                  href={contact.profile_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`block bg-white border border-slate-200 rounded-lg p-4 transition-all ${
                    contact.profile_url
                      ? 'hover:shadow-lg hover:border-blue-300 cursor-pointer'
                      : 'cursor-default'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    {/* Avatar placeholder */}
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-xl font-semibold">
                        {contact.name ? contact.name.charAt(0).toUpperCase() : '?'}
                      </span>
                    </div>

                    {/* Contact Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-slate-900 text-lg truncate hover:text-blue-600 transition-colors">
                            {contact.name || 'Nom inconnu'}
                          </h4>
                          {contact.title && (
                            <p className="text-sm text-slate-600 mt-1 line-clamp-2">
                              {contact.title}
                            </p>
                          )}
                        </div>
                        {contact.profile_url && (
                          <div className="flex-shrink-0 ml-3">
                            <span className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                              <Linkedin size={12} />
                              Voir profil
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-slate-500">
                        {contact.company && (
                          <span className="flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                            <span className="text-blue-600 font-medium">{contact.company}</span>
                          </span>
                        )}
                        {contact.location && (
                          <span className="flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            {contact.location}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </a>
              ))}
            </div>

            {/* Pagination - only show when search is complete */}
            {totalPages > 1 && !isSearching && (
              <div className="flex items-center justify-center gap-4 mt-6">
                <button
                  onClick={() => loadPageResults(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={16} />
                  Précédent
                </button>
                <span className="text-sm text-slate-600">
                  Page {currentPage} sur {totalPages}
                </span>
                <button
                  onClick={() => loadPageResults(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Suivant
                  <ChevronRight size={16} />
                </button>
              </div>
            )}

            {/* Show loading indicator for more results during search */}
            {isSearching && totalResults > PAGE_SIZE && (
              <div className="text-center mt-4 text-sm text-slate-500">
                Affichage des {PAGE_SIZE} premiers résultats. Plus de résultats en cours de chargement...
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
