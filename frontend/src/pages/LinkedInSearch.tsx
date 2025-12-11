/**
 * LinkedIn Search Page
 * Single Responsibility: Search for contacts on LinkedIn
 */
import React, { useEffect, useState } from 'react';
import { Search, Linkedin, ExternalLink, AlertCircle, Activity } from 'lucide-react';
import { linkedInApi } from '../api/linkedin.api';
import { LinkedInStatus, type LinkedInContact, type LinkedInStatusResponse, type RateLimitStatus } from '../types/linkedin';
import { TRANSLATIONS } from '../constants/translations';

const T = TRANSLATIONS.pages.linkedin;

/**
 * Contact Card Component (DRY - reusable contact display)
 */
function ContactCard({ contact }: { contact: LinkedInContact }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold text-slate-900">
            {contact.name || 'Nom inconnu'}
          </h3>
          {contact.title && (
            <p className="text-sm text-slate-600 mt-1">{contact.title}</p>
          )}
          {contact.company && (
            <p className="text-sm text-blue-600 mt-1">{contact.company}</p>
          )}
          {contact.location && (
            <p className="text-sm text-slate-500 mt-1">{contact.location}</p>
          )}
        </div>
        {contact.profile_url && (
          <a
            href={contact.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 p-2"
            title={T.viewProfile}
          >
            <ExternalLink size={18} />
          </a>
        )}
      </div>
    </div>
  );
}

/**
 * Status Indicator Component with Rate Limit Info
 */
function StatusIndicator({ status, rateLimit }: { status: LinkedInStatus; rateLimit: RateLimitStatus | null }) {
  const isConnected = status === LinkedInStatus.CONNECTED;
  const isBusy = status === LinkedInStatus.BUSY;

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className={`flex items-center gap-2 text-sm ${
        isConnected ? 'text-green-600' : isBusy ? 'text-blue-600' : 'text-slate-500'
      }`}>
        <span className={`w-2 h-2 rounded-full ${
          isConnected ? 'bg-green-500' : isBusy ? 'bg-blue-500 animate-pulse' : 'bg-slate-400'
        }`} />
        {T.statusLabels[status] || T.statusLabels.disconnected}
      </div>

      {/* Rate Limit Badge - Only show when connected */}
      {isConnected && rateLimit && (
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <Activity size={14} className="text-blue-500" />
          <span className={rateLimit.searches_remaining_hour <= 5 ? 'text-amber-600 font-medium' : ''}>
            {rateLimit.searches_remaining_hour}/{rateLimit.limits.per_hour} cette heure
          </span>
          <span className="text-slate-300">|</span>
          <span className={rateLimit.searches_remaining_today <= 10 ? 'text-amber-600 font-medium' : ''}>
            {rateLimit.searches_remaining_today}/{rateLimit.limits.per_day} aujourd'hui
          </span>
          {rateLimit.cooldown_remaining_minutes > 0 && (
            <>
              <span className="text-slate-300">|</span>
              <span className="text-amber-600 font-medium">
                Pause: {rateLimit.cooldown_remaining_minutes}min
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function LinkedInSearch() {
  const [statusData, setStatusData] = useState<LinkedInStatusResponse | null>(null);
  const [rateLimitData, setRateLimitData] = useState<RateLimitStatus | null>(null);
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(50); // Default 50 results
  const [contacts, setContacts] = useState<LinkedInContact[]>([]);
  const [totalFound, setTotalFound] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const loadStatus = async () => {
    try {
      const data = await linkedInApi.getStatus();
      setStatusData(data);

      // Load rate limit status if connected
      if (data.status === LinkedInStatus.CONNECTED) {
        try {
          const rateLimit = await linkedInApi.getRateLimitStatus();
          setRateLimitData(rateLimit);
        } catch (err) {
          console.error('Failed to load rate limit status:', err);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement du statut');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setError('');
    setIsSearching(true);
    setHasSearched(true);

    try {
      const response = await linkedInApi.search({ query: query.trim(), limit });
      setContacts(response.contacts);
      setTotalFound(response.total_found);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la recherche');
      setContacts([]);
      setTotalFound(0);
    } finally {
      setIsSearching(false);
      // Refresh status in case it changed (e.g., busy -> connected)
      await loadStatus();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  const isConnected = statusData?.status === LinkedInStatus.CONNECTED;
  const isBusy = statusData?.status === LinkedInStatus.BUSY;
  const canSearch = isConnected || isBusy;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Linkedin className="text-blue-600" />
          {T.search}
        </h1>
        <p className="text-slate-600 mt-1">
          Recherchez des contacts professionnels sur LinkedIn
        </p>
      </div>

      {/* Status Indicator with Rate Limit Info */}
      <div className="mb-6">
        <StatusIndicator status={statusData?.status || LinkedInStatus.DISCONNECTED} rateLimit={rateLimitData} />
      </div>

      {!canSearch ? (
        /* Not Connected Warning */
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <p className="text-yellow-800 font-medium">LinkedIn non connecté</p>
            <p className="text-yellow-700 text-sm mt-1">{T.notConnected}</p>
          </div>
        </div>
      ) : (
        <>
          {/* Search Form */}
          <form onSubmit={handleSearch} className="mb-6">
            <div className="flex gap-3 flex-wrap">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={T.searchPlaceholder}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isSearching}
                />
              </div>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                disabled={isSearching}
                className="px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-700"
              >
                <option value={10}>10 résultats</option>
                <option value={25}>25 résultats</option>
                <option value={50}>50 résultats</option>
                <option value={75}>75 résultats</option>
                <option value={100}>100 résultats</option>
              </select>
              <button
                type="submit"
                disabled={isSearching || !query.trim()}
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSearching ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    Recherche...
                  </span>
                ) : (
                  T.searchButton
                )}
              </button>
            </div>
            {isSearching && limit > 10 && (
              <p className="text-sm text-slate-500 mt-2">
                Chargement de {limit} résultats... Cela peut prendre quelques secondes.
              </p>
            )}
          </form>

          {/* Error Message */}
          {error && (
            <div className="mb-4 bg-red-50 text-red-600 p-3 rounded-md text-sm">
              {error}
            </div>
          )}

          {/* Results */}
          {hasSearched && (
            <div>
              {/* Results Header */}
              <div className="mb-4 flex items-center justify-between">
                <p className="text-slate-600">
                  <span className="font-semibold text-slate-900">{totalFound}</span>{' '}
                  {T.resultsCount}
                </p>
              </div>

              {/* Results Grid */}
              {contacts.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {contacts.map((contact, index) => (
                    <ContactCard key={index} contact={contact} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500">
                  {T.noResults}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
