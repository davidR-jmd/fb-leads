import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, ChevronDown, LogOut, Users, Shield, Linkedin } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export default function Header() {
  const { user, isAdmin, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);

  const displayName = user?.full_name || 'Utilisateur';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      {/* Menu icon */}
      <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
        <Menu size={20} className="text-slate-600" />
      </button>

      {/* User section */}
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="flex items-center gap-3 hover:bg-slate-50 rounded-lg px-2 py-1 transition-colors"
        >
          <span className="text-sm font-medium text-slate-700">{displayName}</span>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-medium">{initial}</span>
            </div>
            <ChevronDown size={16} className="text-slate-500" />
          </div>
        </button>

        {showDropdown && (
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-slate-200 py-1 z-50">
            <div className="px-4 py-2 border-b border-slate-100">
              <p className="text-sm font-medium text-slate-700">{displayName}</p>
              <p className="text-xs text-slate-500">{user?.email}</p>
              {isAdmin && (
                <span className="inline-flex items-center gap-1 mt-1 text-xs text-purple-600">
                  <Shield size={12} />
                  Administrateur
                </span>
              )}
            </div>
            {isAdmin && (
              <>
                <Link
                  to="/admin/users"
                  onClick={() => setShowDropdown(false)}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <Users size={16} />
                  Gestion utilisateurs
                </Link>
                <Link
                  to="/admin/linkedin"
                  onClick={() => setShowDropdown(false)}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <Linkedin size={16} />
                  Configuration LinkedIn
                </Link>
              </>
            )}
            <button
              onClick={() => {
                setShowDropdown(false);
                logout();
              }}
              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              <LogOut size={16} />
              Déconnexion
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
