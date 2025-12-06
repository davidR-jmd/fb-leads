/**
 * LinkedIn Email Verification Modal
 * Single Responsibility: Handle verification code input
 */
import React, { useState } from 'react';
import { X } from 'lucide-react';
import { TRANSLATIONS } from '../constants/translations';

interface LinkedInVerifyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (code: string) => Promise<void>;
  isLoading: boolean;
}

const T = TRANSLATIONS.pages.linkedin;

export default function LinkedInVerifyModal({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}: LinkedInVerifyModalProps) {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!code.trim()) {
      setError('Veuillez entrer le code de vérification');
      return;
    }

    try {
      await onSubmit(code.trim());
      setCode('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la vérification');
    }
  };

  const handleClose = () => {
    setCode('');
    setError('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">{T.verifyTitle}</h3>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-4">
          <p className="text-slate-600 mb-4">{T.verifyMessage}</p>

          {error && (
            <div className="mb-4 bg-red-50 text-red-600 p-3 rounded-md text-sm">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label
              htmlFor="verification-code"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              {T.verifyCode}
            </label>
            <input
              type="text"
              id="verification-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
              disabled={isLoading}
            />
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors"
              disabled={isLoading}
            >
              {T.cancel}
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  Vérification...
                </span>
              ) : (
                T.verifySubmit
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
