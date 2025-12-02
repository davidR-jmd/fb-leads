import React from 'react';
import { TRANSLATIONS } from '../constants/translations';

export default function Historique() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-800 mb-6">
        {TRANSLATIONS.pages.history.title}
      </h1>
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <p className="text-slate-500">{TRANSLATIONS.pages.history.placeholder}</p>
      </div>
    </div>
  );
}
