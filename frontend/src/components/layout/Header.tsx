import React from 'react';
import { Menu, ChevronDown } from 'lucide-react';

interface HeaderProps {
  companyName?: string;
}

export default function Header({ companyName = 'FB Leads' }: HeaderProps) {
  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      {/* Menu icon */}
      <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
        <Menu size={20} className="text-slate-600" />
      </button>

      {/* User/Company section */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-slate-700">{companyName}</span>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">
              {companyName.charAt(0)}
            </span>
          </div>
          <ChevronDown size={16} className="text-slate-500" />
        </div>
      </div>
    </header>
  );
}
