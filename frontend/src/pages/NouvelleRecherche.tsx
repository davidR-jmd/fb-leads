import React from 'react';
import { TRANSLATIONS } from '../constants/translations';

export default function NouvelleRecherche() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-800 mb-6">
        {TRANSLATIONS.pages.newSearch.title}
      </h1>
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <p className="text-slate-500">{TRANSLATIONS.pages.newSearch.placeholder}</p>
      </div>
    </div>
  );
}
