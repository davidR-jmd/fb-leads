/**
 * LinkedIn Settings Page (Admin Only)
 * Single Responsibility: Manage LinkedIn connection configuration
 *
 * Authentication Flow:
 * 1. Primary: Cookie-based auth (li_at cookie) - most reliable
 * 2. Fallback: Manual login in visible browser window
 */
import React, { useEffect, useState } from 'react';
import { Linkedin, HelpCircle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { linkedInApi } from '../api/linkedin.api';
import { LinkedInStatus, LinkedInAuthMethod, type LinkedInStatusResponse } from '../types/linkedin';
import { TRANSLATIONS } from '../constants/translations';
import LinkedInVerifyModal from '../components/LinkedInVerifyModal';

const T = TRANSLATIONS.pages.linkedin;

/**
 * Status badge component (DRY - reusable status display)
 */
function StatusBadge({ status }: { status: LinkedInStatus }) {
  const statusConfig: Record<LinkedInStatus, { color: string; label: string }> = {
    [LinkedInStatus.DISCONNECTED]: { color: 'bg-slate-100 text-slate-800', label: T.statusLabels.disconnected },
    [LinkedInStatus.CONNECTING]: { color: 'bg-yellow-100 text-yellow-800', label: T.statusLabels.connecting },
    [LinkedInStatus.NEED_EMAIL_CODE]: { color: 'bg-orange-100 text-orange-800', label: T.statusLabels.need_email_code },
    [LinkedInStatus.NEED_MANUAL_LOGIN]: { color: 'bg-red-100 text-red-800', label: T.statusLabels.need_manual_login },
    [LinkedInStatus.AWAITING_MANUAL_LOGIN]: { color: 'bg-amber-100 text-amber-800', label: T.statusLabels.awaiting_manual_login },
    [LinkedInStatus.CONNECTED]: { color: 'bg-green-100 text-green-800', label: T.statusLabels.connected },
    [LinkedInStatus.BUSY]: { color: 'bg-blue-100 text-blue-800', label: T.statusLabels.busy },
    [LinkedInStatus.ERROR]: { color: 'bg-red-100 text-red-800', label: T.statusLabels.error },
  };

  const config = statusConfig[status] || statusConfig[LinkedInStatus.DISCONNECTED];

  return (
    <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${config.color}`}>
      {config.label}
    </span>
  );
}

function AuthMethodBadge({ method }: { method: LinkedInAuthMethod | null | undefined }) {
  if (!method) return null;

  const methodConfig: Record<LinkedInAuthMethod, { color: string; label: string }> = {
    [LinkedInAuthMethod.COOKIE]: { color: 'bg-purple-100 text-purple-800', label: T.authMethodLabels.cookie },
    [LinkedInAuthMethod.CREDENTIALS]: { color: 'bg-blue-100 text-blue-800', label: T.authMethodLabels.credentials },
    [LinkedInAuthMethod.MANUAL]: { color: 'bg-teal-100 text-teal-800', label: T.authMethodLabels.manual },
  };

  const config = methodConfig[method];

  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${config.color}`}>
      {config.label}
    </span>
  );
}

export default function LinkedInSettings() {
  const [statusData, setStatusData] = useState<LinkedInStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [showCookieHelp, setShowCookieHelp] = useState(false);

  // Form state - Cookie auth (primary)
  const [cookie, setCookie] = useState('');

  // Form state - Credentials auth (deprecated but kept for backwards compat)
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showCredentialsForm, setShowCredentialsForm] = useState(false);

  const loadStatus = async () => {
    try {
      const data = await linkedInApi.getStatus();
      setStatusData(data);

      // Auto-show verify modal if needed
      if (data.status === LinkedInStatus.NEED_EMAIL_CODE) {
        setShowVerifyModal(true);
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

  // Primary: Cookie-based authentication
  const handleConnectWithCookie = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsSubmitting(true);

    try {
      const response = await linkedInApi.connectWithCookie({ cookie });

      if (response.status === LinkedInStatus.CONNECTED) {
        setCookie('');
        setSuccessMessage(response.message || 'Connecté avec succès');
        await loadStatus();
      } else {
        setError(response.message || 'Échec de la connexion');
        setStatusData((prev) => prev ? { ...prev, status: response.status } : null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la connexion');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Fallback: Open browser for manual login
  const handleOpenBrowser = async () => {
    setError('');
    setSuccessMessage('');
    setIsSubmitting(true);

    try {
      const response = await linkedInApi.openBrowserForManualLogin();
      setStatusData((prev) => prev ? { ...prev, status: response.status } : null);
      setSuccessMessage(response.message || 'Navigateur ouvert');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'ouverture du navigateur');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Deprecated: Credentials-based authentication (kept for backwards compat)
  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsSubmitting(true);

    try {
      const response = await linkedInApi.connect({ email, password });
      setStatusData({ status: response.status, email });

      if (response.status === LinkedInStatus.NEED_EMAIL_CODE) {
        setShowVerifyModal(true);
      } else if (response.status === LinkedInStatus.CONNECTED) {
        setEmail('');
        setPassword('');
        await loadStatus();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la connexion');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyCode = async (code: string) => {
    const response = await linkedInApi.verifyCode({ code });

    if (response.status === LinkedInStatus.CONNECTED) {
      setShowVerifyModal(false);
      setEmail('');
      setPassword('');
      await loadStatus();
    } else {
      throw new Error(response.message || 'Code invalide');
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Êtes-vous sûr de vouloir déconnecter LinkedIn ?')) {
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await linkedInApi.disconnect();
      await loadStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la déconnexion');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleValidateSession = async () => {
    setIsSubmitting(true);
    setError('');

    try {
      const response = await linkedInApi.validateSession();
      if (response.status === LinkedInStatus.CONNECTED) {
        await loadStatus();
      } else {
        setError(response.message || 'Session non valide');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la validation');
    } finally {
      setIsSubmitting(false);
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

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Linkedin className="text-blue-600" />
          {T.title}
        </h1>
        <p className="text-slate-600 mt-1">
          Configurez la connexion LinkedIn pour la recherche de contacts
        </p>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-600 p-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="mb-4 bg-green-50 text-green-600 p-3 rounded-md text-sm">
          {successMessage}
        </div>
      )}

      <div className="bg-white shadow-sm rounded-lg overflow-hidden max-w-xl">
        <div className="p-6">
          {/* Status Display */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              {T.status}
            </label>
            <div className="flex items-center gap-2">
              <StatusBadge status={statusData?.status || LinkedInStatus.DISCONNECTED} />
              <AuthMethodBadge method={statusData?.auth_method} />
            </div>
          </div>

          {isConnected ? (
            /* Connected State */
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {T.account}
                </label>
                <p className="text-slate-900">{statusData?.email}</p>
              </div>

              {statusData?.last_connected && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {T.lastConnected}
                  </label>
                  <p className="text-slate-900">
                    {new Date(statusData.last_connected).toLocaleDateString('fr-FR', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              )}

              <button
                onClick={handleDisconnect}
                disabled={isSubmitting}
                className="w-full mt-4 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Déconnexion...' : T.disconnect}
              </button>
            </div>
          ) : statusData?.status === LinkedInStatus.AWAITING_MANUAL_LOGIN ? (
            /* Awaiting Manual Login State */
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm text-amber-800">
                  {T.manualAuth.waitingMessage}
                </p>
              </div>

              <button
                type="button"
                onClick={handleValidateSession}
                disabled={isSubmitting}
                className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    Vérification...
                  </span>
                ) : (
                  T.manualAuth.validateSession
                )}
              </button>
            </div>
          ) : (
            /* Disconnected State - Show Auth Options */
            <div className="space-y-6">
              {/* Option 1: Cookie Auth (Primary) */}
              <div className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-slate-800">
                    {T.cookieAuth.title}
                  </h3>
                  <button
                    type="button"
                    onClick={() => setShowCookieHelp(!showCookieHelp)}
                    className="text-slate-500 hover:text-slate-700 flex items-center gap-1 text-xs"
                  >
                    <HelpCircle size={14} />
                    {T.cookieAuth.howToGet}
                    {showCookieHelp ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>

                {showCookieHelp && (
                  <div className="mb-4 bg-blue-50 border border-blue-200 rounded-md p-3">
                    <ul className="text-xs text-blue-800 space-y-1">
                      {T.cookieAuth.howToGetSteps.map((step, index) => (
                        <li key={index}>{step}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <p className="text-xs text-slate-500 mb-3">
                  {T.cookieAuth.description}
                </p>

                <form onSubmit={handleConnectWithCookie} className="space-y-3">
                  <textarea
                    value={cookie}
                    onChange={(e) => setCookie(e.target.value)}
                    placeholder={T.cookieAuth.placeholder}
                    rows={3}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono"
                    disabled={isSubmitting}
                  />

                  <button
                    type="submit"
                    disabled={isSubmitting || !cookie.trim()}
                    className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                        Connexion...
                      </span>
                    ) : (
                      T.cookieAuth.connect
                    )}
                  </button>
                </form>
              </div>

              {/* Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 bg-white text-slate-500">ou</span>
                </div>
              </div>

              {/* Option 2: Manual Login (Fallback) */}
              <div className="border border-slate-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-slate-800 mb-2">
                  {T.manualAuth.title}
                </h3>
                <p className="text-xs text-slate-500 mb-3">
                  {T.manualAuth.description}
                </p>

                <button
                  type="button"
                  onClick={handleOpenBrowser}
                  disabled={isSubmitting}
                  className="w-full px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <ExternalLink size={16} />
                  {isSubmitting ? 'Ouverture...' : T.manualAuth.openBrowser}
                </button>
              </div>

              {/* Option 3: Legacy Credentials (Hidden by default) */}
              <div className="border-t border-slate-200 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCredentialsForm(!showCredentialsForm)}
                  className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1"
                >
                  {showCredentialsForm ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  Connexion par identifiants (non recommandé)
                </button>

                {showCredentialsForm && (
                  <form onSubmit={handleConnect} className="mt-3 space-y-3">
                    <div>
                      <label
                        htmlFor="linkedin-email"
                        className="block text-xs font-medium text-slate-600 mb-1"
                      >
                        {T.email}
                      </label>
                      <input
                        type="email"
                        id="linkedin-email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="exemple@email.com"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        required
                        disabled={isSubmitting}
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="linkedin-password"
                        className="block text-xs font-medium text-slate-600 mb-1"
                      >
                        {T.password}
                      </label>
                      <input
                        type="password"
                        id="linkedin-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        required
                        disabled={isSubmitting}
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-slate-600 rounded-md hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSubmitting ? 'Connexion...' : T.connect}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}

          {/* Error message from status */}
          {statusData?.error_message && (
            <div className="mt-4 bg-red-50 text-red-600 p-3 rounded-md text-sm">
              {statusData.error_message}
            </div>
          )}
        </div>
      </div>

      {/* Verification Modal */}
      <LinkedInVerifyModal
        isOpen={showVerifyModal}
        onClose={() => setShowVerifyModal(false)}
        onSubmit={handleVerifyCode}
        isLoading={isSubmitting}
      />
    </div>
  );
}
