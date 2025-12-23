import React, { useState } from 'react';
import {
  Search,
  Building2,
  User,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle,
  Linkedin,
  Euro,
  Users,
  MapPin,
  FileText,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';
import { prospectsApi } from '../api/prospects.api';
import type {
  SimpleSearchResponse,
  CompanyData,
  ContactData,
  ProspectResult,
  SearchFilters,
  CompanyType,
} from '../types/prospects';
import {
  COMMON_JOB_FUNCTIONS,
  FRENCH_DEPARTEMENTS,
  EMPLOYEE_RANGES,
  REVENUE_RANGES,
  SearchStatus,
} from '../types/prospects';

export default function ProspectFinder() {
  // Search fields
  const [jobFunction, setJobFunction] = useState('');
  const [companyName, setCompanyName] = useState('');

  // Filters (collapsible)
  const [showFilters, setShowFilters] = useState(false);
  const [selectedDepartements, setSelectedDepartements] = useState<string[]>([]);
  const [employeeRangeIndex, setEmployeeRangeIndex] = useState(0);
  const [revenueRangeIndex, setRevenueRangeIndex] = useState(0);
  const [companyType, setCompanyType] = useState<CompanyType>('all');

  // UI state
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simpleResult, setSimpleResult] = useState<SimpleSearchResponse | null>(null);
  const [advancedResults, setAdvancedResults] = useState<ProspectResult[]>([]);
  const [showJobSuggestions, setShowJobSuggestions] = useState(false);
  const [showDeptDropdown, setShowDeptDropdown] = useState(false);

  const hasFilters = selectedDepartements.length > 0 || employeeRangeIndex > 0 || revenueRangeIndex > 0 || companyType !== 'all';

  const handleSearch = async () => {
    if (!jobFunction.trim()) {
      setError('Veuillez saisir une fonction');
      return;
    }

    // Must have either company name OR filters
    if (!companyName.trim() && !hasFilters) {
      setError('Veuillez saisir un nom d\'entreprise ou utiliser les filtres');
      return;
    }

    setIsSearching(true);
    setError(null);
    setSimpleResult(null);
    setAdvancedResults([]);

    try {
      // If company name is provided, use simple search
      if (companyName.trim()) {
        const response = await prospectsApi.simpleSearch({
          job_function: jobFunction.trim(),
          company_name: companyName.trim(),
        });
        setSimpleResult(response);
      } else {
        // Use advanced search with filters
        const employeeRange = EMPLOYEE_RANGES[employeeRangeIndex];
        const revenueRange = REVENUE_RANGES[revenueRangeIndex];

        const filters: SearchFilters = {
          departements: selectedDepartements.length > 0 ? selectedDepartements : undefined,
          size_min: employeeRange.min,
          size_max: employeeRange.max,
          revenue_min: revenueRange.min,
          revenue_max: revenueRange.max,
          is_public: companyType === 'all' ? null : companyType === 'public',
        };

        const response = await prospectsApi.search({
          job_function: jobFunction.trim(),
          filters,
        });

        if (response.status === SearchStatus.COMPLETED && response.job_id) {
          const resultsResponse = await prospectsApi.getSearchResults(response.job_id);
          setAdvancedResults(resultsResponse.results);
        } else if (response.status === SearchStatus.FAILED) {
          setError(response.message || 'Aucune entreprise trouvee avec ces criteres');
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la recherche');
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isSearching) {
      handleSearch();
    }
  };

  const toggleDepartement = (code: string) => {
    setSelectedDepartements((prev) =>
      prev.includes(code) ? prev.filter((d) => d !== code) : [...prev, code]
    );
  };

  const removeDepartement = (code: string) => {
    setSelectedDepartements((prev) => prev.filter((d) => d !== code));
  };

  const clearFilters = () => {
    setSelectedDepartements([]);
    setEmployeeRangeIndex(0);
    setRevenueRangeIndex(0);
    setCompanyType('all');
  };

  const filteredSuggestions = COMMON_JOB_FUNCTIONS.filter((fn) =>
    fn.toLowerCase().includes(jobFunction.toLowerCase())
  );

  const hasResults = simpleResult || advancedResults.length > 0;
  const canSearch = jobFunction.trim() && (companyName.trim() || hasFilters);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Page Title */}
      <h1 className="text-2xl font-semibold text-slate-800 mb-2">Prospect Finder</h1>
      <p className="text-slate-600 mb-6">
        Trouvez des contacts qualifies avec leurs profils LinkedIn
      </p>

      {/* Search Form */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        {/* Job Function Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Fonction recherchee *
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              value={jobFunction}
              onChange={(e) => setJobFunction(e.target.value)}
              onFocus={() => setShowJobSuggestions(true)}
              onBlur={() => setTimeout(() => setShowJobSuggestions(false), 200)}
              onKeyPress={handleKeyPress}
              placeholder="Ex: Directeur Commercial, Responsable Achats..."
              className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={isSearching}
            />
            {/* Suggestions dropdown */}
            {showJobSuggestions && filteredSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                {filteredSuggestions.map((fn) => (
                  <button
                    key={fn}
                    type="button"
                    onClick={() => {
                      setJobFunction(fn);
                      setShowJobSuggestions(false);
                    }}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50 first:rounded-t-lg last:rounded-b-lg"
                  >
                    {fn}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Company Name Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Nom de l'entreprise {!hasFilters && '*'}
          </label>
          <div className="relative">
            <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ex: Carrefour, FNAC..."
              className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={isSearching}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Laissez vide pour rechercher par filtres
          </p>
        </div>

        {/* Filters Section (Collapsible) */}
        <div className="border-t border-slate-200 pt-4">
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center justify-between w-full text-left"
            disabled={isSearching}
          >
            <span className="text-sm font-medium text-slate-700 flex items-center gap-2">
              Filtres avances
              {hasFilters && (
                <span className="px-2 py-0.5 bg-teal-100 text-teal-700 rounded-full text-xs">
                  {selectedDepartements.length + (employeeRangeIndex > 0 ? 1 : 0) + (revenueRangeIndex > 0 ? 1 : 0) + (companyType !== 'all' ? 1 : 0)} actif(s)
                </span>
              )}
            </span>
            {showFilters ? (
              <ChevronUp size={18} className="text-slate-400" />
            ) : (
              <ChevronDown size={18} className="text-slate-400" />
            )}
          </button>

          {showFilters && (
            <div className="mt-4 space-y-4">
              {/* Departements Multi-select */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Departements
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowDeptDropdown(!showDeptDropdown)}
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-left flex items-center justify-between focus:outline-none focus:ring-2 focus:ring-teal-500"
                    disabled={isSearching}
                  >
                    <span className="text-slate-600">
                      {selectedDepartements.length === 0
                        ? 'Tous les departements'
                        : `${selectedDepartements.length} departement(s) selectionne(s)`}
                    </span>
                    <ChevronDown size={18} className="text-slate-400" />
                  </button>

                  {showDeptDropdown && (
                    <div className="absolute z-20 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {FRENCH_DEPARTEMENTS.map((dept) => (
                        <label
                          key={dept.code}
                          className="flex items-center px-4 py-2 hover:bg-slate-50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedDepartements.includes(dept.code)}
                            onChange={() => toggleDepartement(dept.code)}
                            className="mr-3 h-4 w-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
                          />
                          <span className="text-sm">
                            {dept.code} - {dept.name}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                {/* Selected departments chips */}
                {selectedDepartements.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedDepartements.map((code) => (
                      <span
                        key={code}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-teal-100 text-teal-700 rounded-full text-sm"
                      >
                        {code}
                        <button
                          type="button"
                          onClick={() => removeDepartement(code)}
                          className="hover:bg-teal-200 rounded-full p-0.5"
                        >
                          <X size={14} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Employee Range & Revenue Range */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Employee Range */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    <Users size={14} className="inline mr-1" />
                    Taille de l'entreprise
                  </label>
                  <select
                    value={employeeRangeIndex}
                    onChange={(e) => setEmployeeRangeIndex(Number(e.target.value))}
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                    disabled={isSearching}
                  >
                    {EMPLOYEE_RANGES.map((range, index) => (
                      <option key={index} value={index}>
                        {range.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Revenue Range */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    <Euro size={14} className="inline mr-1" />
                    Chiffre d'affaires
                  </label>
                  <select
                    value={revenueRangeIndex}
                    onChange={(e) => setRevenueRangeIndex(Number(e.target.value))}
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                    disabled={isSearching}
                  >
                    {REVENUE_RANGES.map((range, index) => (
                      <option key={index} value={index}>
                        {range.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Company Type (Private/Public) */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Type d'entreprise
                </label>
                <div className="flex gap-2">
                  {[
                    { value: 'all', label: 'Toutes' },
                    { value: 'private', label: 'Privee' },
                    { value: 'public', label: 'Publique (SA)' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setCompanyType(option.value as CompanyType)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        companyType === option.value
                          ? 'bg-teal-100 text-teal-700 border-2 border-teal-500'
                          : 'bg-slate-100 text-slate-600 border-2 border-transparent hover:bg-slate-200'
                      }`}
                      disabled={isSearching}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Clear Filters */}
              {hasFilters && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="text-sm text-slate-500 hover:text-slate-700 underline"
                  disabled={isSearching}
                >
                  Effacer les filtres
                </button>
              )}
            </div>
          )}
        </div>

        {/* Search Button */}
        <button
          onClick={handleSearch}
          disabled={isSearching || !canSearch}
          className="w-full mt-6 py-3 bg-gradient-to-r from-teal-600 to-teal-500 text-white rounded-lg font-medium hover:from-teal-700 hover:to-teal-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isSearching ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Recherche en cours...
            </>
          ) : (
            <>
              <Search size={20} />
              Rechercher
            </>
          )}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-start gap-3 p-4 mb-6 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Simple Search Results */}
      {simpleResult && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-800">Resultat</h2>
              {simpleResult.linkedin_found ? (
                <span className="flex items-center gap-1 text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">
                  <CheckCircle size={16} />
                  {simpleResult.profiles_count} profil(s) trouve(s)
                </span>
              ) : (
                <span className="flex items-center gap-1 text-sm text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
                  <AlertCircle size={16} />
                  Aucun profil trouve
                </span>
              )}
            </div>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Entreprise
                </h3>
                <CompanyCard company={simpleResult.company} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Contacts - {simpleResult.searched_function}
                </h3>
                <ContactsList contacts={simpleResult.contacts} linkedinFound={simpleResult.linkedin_found} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Advanced Search Results */}
      {advancedResults.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <h2 className="text-lg font-semibold text-slate-800">
              {advancedResults.length} entreprise(s) trouvee(s)
            </h2>
          </div>

          <div className="divide-y divide-slate-200">
            {advancedResults.map((result, index) => (
              <div key={index} className="p-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <CompanyCard company={result.company} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                      {result.searched_function}
                      {result.profiles_count > 0 && (
                        <span className="ml-2 text-xs text-teal-600">
                          ({result.profiles_count} profil{result.profiles_count > 1 ? 's' : ''})
                        </span>
                      )}
                    </h3>
                    <ContactsList
                      contacts={result.contacts || []}
                      linkedinFound={result.linkedin_found}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Instructions */}
      {!hasResults && !isSearching && (
        <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
          <h3 className="font-medium text-slate-800 mb-3">Comment utiliser</h3>
          <ol className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">
                1
              </span>
              <span>Entrez la fonction recherchee (ex: Directeur Commercial)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">
                2
              </span>
              <span>
                Saisissez un nom d'entreprise <strong>ou</strong> utilisez les filtres avances
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">
                3
              </span>
              <span>Cliquez sur le lien LinkedIn pour ouvrir le profil</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">
                4
              </span>
              <span>Utilisez l'extension Lusha pour obtenir le telephone/email</span>
            </li>
          </ol>
        </div>
      )}

      {/* Click outside to close dropdowns */}
      {showDeptDropdown && (
        <div className="fixed inset-0 z-10" onClick={() => setShowDeptDropdown(false)} />
      )}
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function CompanyCard({ company }: { company: CompanyData }) {
  const formatRevenue = (revenue: number | null | undefined): string => {
    if (!revenue) return '-';
    if (revenue >= 1_000_000_000) {
      return `${(revenue / 1_000_000_000).toFixed(1)} Md`;
    }
    if (revenue >= 1_000_000) {
      return `${(revenue / 1_000_000).toFixed(1)} M`;
    }
    if (revenue >= 1_000) {
      return `${(revenue / 1_000).toFixed(0)} k`;
    }
    return revenue.toString();
  };

  return (
    <div className="bg-slate-50 rounded-lg p-4 space-y-3">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center flex-shrink-0">
          <Building2 className="text-teal-600" size={20} />
        </div>
        <div>
          <h4 className="font-semibold text-slate-800">{company.name}</h4>
          {company.legal_form && <span className="text-xs text-slate-500">{company.legal_form}</span>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        {company.siren && (
          <div className="flex items-center gap-2 text-slate-600">
            <FileText size={14} className="text-slate-400" />
            <span>SIREN: {company.siren}</span>
          </div>
        )}

        {(company.employees || company.employees_range) && (
          <div className="flex items-center gap-2 text-slate-600">
            <Users size={14} className="text-slate-400" />
            <span>{company.employees_range || `${company.employees} employes`}</span>
          </div>
        )}

        {company.revenue && (
          <div className="flex items-center gap-2 text-slate-600">
            <Euro size={14} className="text-slate-400" />
            <span>CA: {formatRevenue(company.revenue)}</span>
          </div>
        )}

        {company.address?.city && (
          <div className="flex items-center gap-2 text-slate-600">
            <MapPin size={14} className="text-slate-400" />
            <span>{company.address.city}</span>
          </div>
        )}
      </div>

      {company.naf_label && (
        <div className="text-xs text-slate-500 pt-2 border-t border-slate-200">{company.naf_label}</div>
      )}
    </div>
  );
}

function ContactsList({ contacts, linkedinFound }: { contacts: ContactData[]; linkedinFound: boolean }) {
  if (!contacts || contacts.length === 0) {
    return (
      <div className="bg-amber-50 rounded-lg p-4 text-center">
        <AlertCircle className="mx-auto text-amber-500 mb-2" size={24} />
        <p className="text-sm text-amber-700">Aucun profil LinkedIn trouve pour cette fonction</p>
        <p className="text-xs text-amber-600 mt-1">
          Essayez avec une fonction differente ou verifiez l'orthographe
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {contacts.map((contact, index) => (
        <div key={index} className="bg-slate-50 rounded-lg p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-white font-semibold">
                {contact.name ? contact.name.charAt(0).toUpperCase() : '?'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-slate-800 truncate">{contact.name || 'Nom inconnu'}</h4>
              {contact.title && <p className="text-sm text-slate-600 line-clamp-2">{contact.title}</p>}
            </div>
          </div>

          {contact.linkedin_url && (
            <a
              href={contact.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2 bg-[#0A66C2] text-white rounded-lg text-sm font-medium hover:bg-[#004182] transition-colors"
            >
              <Linkedin size={16} />
              Ouvrir LinkedIn
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      ))}

      <div className="text-xs text-slate-500 text-center pt-2 border-t border-slate-200">
        Utilisez l'extension Lusha pour obtenir les coordonnees
      </div>
    </div>
  );
}
