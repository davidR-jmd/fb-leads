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
} from 'lucide-react';
import { prospectsApi } from '../api/prospects.api';
import type { SimpleSearchResponse, CompanyData, ContactData } from '../types/prospects';
import { COMMON_JOB_FUNCTIONS } from '../types/prospects';

export default function ProspectFinder() {
  // Form state
  const [jobFunction, setJobFunction] = useState('');
  const [companyName, setCompanyName] = useState('');

  // Search state
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimpleSearchResponse | null>(null);

  // Suggestions visibility
  const [showJobSuggestions, setShowJobSuggestions] = useState(false);

  const handleSearch = async () => {
    if (!jobFunction.trim() || !companyName.trim()) {
      setError('Veuillez remplir tous les champs');
      return;
    }

    setIsSearching(true);
    setError(null);
    setResult(null);

    try {
      const response = await prospectsApi.simpleSearch({
        job_function: jobFunction.trim(),
        company_name: companyName.trim(),
      });
      setResult(response);
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

  const filteredSuggestions = COMMON_JOB_FUNCTIONS.filter((fn) =>
    fn.toLowerCase().includes(jobFunction.toLowerCase())
  );

  return (
    <div className="max-w-4xl mx-auto">
      {/* Page Title */}
      <h1 className="text-2xl font-semibold text-slate-800 mb-2">Prospect Finder</h1>
      <p className="text-slate-600 mb-6">
        Trouvez des contacts qualifies avec leurs profils LinkedIn
      </p>

      {/* Search Form */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Job Function Input */}
          <div className="relative">
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
                placeholder="Ex: Directeur Commercial"
                className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                disabled={isSearching}
              />
            </div>
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

          {/* Company Name Input */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Nom de l'entreprise *
            </label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ex: Carrefour"
                className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                disabled={isSearching}
              />
            </div>
          </div>
        </div>

        {/* Search Button */}
        <button
          onClick={handleSearch}
          disabled={isSearching || !jobFunction.trim() || !companyName.trim()}
          className="w-full py-3 bg-gradient-to-r from-teal-600 to-teal-500 text-white rounded-lg font-medium hover:from-teal-700 hover:to-teal-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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

      {/* Results */}
      {result && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          {/* Result Header */}
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-800">Resultat</h2>
              {result.linkedin_found ? (
                <span className="flex items-center gap-1 text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">
                  <CheckCircle size={16} />
                  Profil LinkedIn trouve
                </span>
              ) : (
                <span className="flex items-center gap-1 text-sm text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
                  <AlertCircle size={16} />
                  Profil LinkedIn non trouve
                </span>
              )}
            </div>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Company Info */}
              <div>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Entreprise
                </h3>
                <CompanyCard company={result.company} />
              </div>

              {/* Contacts Info */}
              <div>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Contacts - {result.searched_function} ({result.profiles_count} profils)
                </h3>
                <ContactsList contacts={result.contacts} linkedinFound={result.linkedin_found} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      {!result && !isSearching && (
        <div className="bg-slate-50 rounded-lg border border-slate-200 p-6">
          <h3 className="font-medium text-slate-800 mb-3">Comment utiliser</h3>
          <ol className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">1</span>
              <span>Entrez la fonction recherchee (ex: Directeur Commercial)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">2</span>
              <span>Entrez le nom de l'entreprise cible</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">3</span>
              <span>Cliquez sur le lien LinkedIn pour ouvrir le profil</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center text-xs font-medium">4</span>
              <span>Utilisez l'extension Lusha pour obtenir le telephone/email</span>
            </li>
          </ol>
        </div>
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
      {/* Company Name */}
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center flex-shrink-0">
          <Building2 className="text-teal-600" size={20} />
        </div>
        <div>
          <h4 className="font-semibold text-slate-800">{company.name}</h4>
          {company.legal_form && (
            <span className="text-xs text-slate-500">{company.legal_form}</span>
          )}
        </div>
      </div>

      {/* Company Details */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {company.siren && (
          <div className="flex items-center gap-2 text-slate-600">
            <FileText size={14} className="text-slate-400" />
            <span>SIREN: {company.siren}</span>
          </div>
        )}

        {company.employees && (
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

      {/* Industry */}
      {company.naf_label && (
        <div className="text-xs text-slate-500 pt-2 border-t border-slate-200">
          {company.naf_label}
        </div>
      )}
    </div>
  );
}

function ContactsList({
  contacts,
  linkedinFound,
}: {
  contacts: ContactData[];
  linkedinFound: boolean;
}) {
  if (!contacts || contacts.length === 0) {
    return (
      <div className="bg-amber-50 rounded-lg p-4 text-center">
        <AlertCircle className="mx-auto text-amber-500 mb-2" size={24} />
        <p className="text-sm text-amber-700">
          Aucun profil LinkedIn trouve pour cette fonction
        </p>
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
          {/* Contact Avatar & Name */}
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-white font-semibold">
                {contact.name ? contact.name.charAt(0).toUpperCase() : '?'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-slate-800 truncate">
                {contact.name || 'Nom inconnu'}
              </h4>
              {contact.title && (
                <p className="text-sm text-slate-600 line-clamp-2">{contact.title}</p>
              )}
            </div>
          </div>

          {/* LinkedIn Button */}
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

      {/* Lusha Reminder */}
      <div className="text-xs text-slate-500 text-center pt-2 border-t border-slate-200">
        Utilisez l'extension Lusha pour obtenir les coordonnees
      </div>
    </div>
  );
}
