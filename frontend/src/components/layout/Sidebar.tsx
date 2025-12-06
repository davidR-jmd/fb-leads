import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Search, History, Settings, Linkedin } from 'lucide-react';
import { cn } from '../../lib/utils';
import { TRANSLATIONS } from '../../constants/translations';
import { useAuth } from '../../hooks/useAuth';

/**
 * Navigation item configuration
 * Open/Closed Principle: Easy to add new nav items without modifying component logic
 */
interface NavItemConfig {
  path: string;
  icon: React.ReactNode;
  label: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItemConfig[] = [
  { path: '/', icon: <LayoutDashboard size={20} />, label: TRANSLATIONS.nav.dashboard },
  { path: '/recherche', icon: <Search size={20} />, label: TRANSLATIONS.nav.newSearch },
  { path: '/linkedin/search', icon: <Linkedin size={20} />, label: TRANSLATIONS.navExtended.linkedin },
  { path: '/historique', icon: <History size={20} />, label: TRANSLATIONS.nav.history },
  { path: '/configuration', icon: <Settings size={20} />, label: TRANSLATIONS.nav.settings },
];

/**
 * Single navigation item component
 * Single Responsibility: Only handles rendering a single nav link
 */
interface NavItemProps {
  path: string;
  icon: React.ReactNode;
  label: string;
}

function NavItem({ path, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={path}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors',
          isActive
            ? 'bg-blue-600 text-white'
            : 'text-slate-300 hover:bg-slate-700 hover:text-white'
        )
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

/**
 * Sidebar component
 * Single Responsibility: Only handles sidebar layout and navigation structure
 */
export default function Sidebar() {
  const { isAdmin } = useAuth();

  // Filter nav items based on user role
  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || isAdmin);

  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-slate-800 flex flex-col">
      {/* Logo */}
      <div className="p-4 flex items-center justify-center">
        <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
          <span className="text-white text-xl font-bold">F</span>
        </div>
      </div>

      {/* Navigation - DRY: Maps over config instead of repeating JSX */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {visibleItems.map((item) => (
          <NavItem
            key={item.path}
            path={item.path}
            icon={item.icon}
            label={item.label}
          />
        ))}
      </nav>
    </aside>
  );
}
