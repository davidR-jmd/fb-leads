import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { TRANSLATIONS } from '../constants/translations';
import Stepper from '../components/Stepper';
import FileUploadZone from '../components/FileUploadZone';
import SelectDropdown from '../components/SelectDropdown';

const t = TRANSLATIONS.pages.newSearch;

const STEPS = [
  { number: 1, label: t.steps.import },
  { number: 2, label: t.steps.validation },
  { number: 3, label: t.steps.synchronisation },
];

const PROFILE_OPTIONS = [
  { value: 'marketing_director', label: t.profiles.marketingDirector },
  { value: 'sales_director', label: t.profiles.salesDirector },
  { value: 'ceo', label: t.profiles.ceo },
  { value: 'cto', label: t.profiles.cto },
  { value: 'hr', label: t.profiles.hr },
];

export default function NouvelleRecherche() {
  const [currentStep, setCurrentStep] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [columnMapping, setColumnMapping] = useState({
    companyName: '',
    website: '',
  });
  const [profile, setProfile] = useState('marketing_director');
  const [columns, setColumns] = useState<string[]>([]);

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile);

    // Parse CSV/Excel headers for column mapping
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (text) {
        const firstLine = text.split('\n')[0];
        const headers = firstLine.split(/[,;\t]/).map((h) => h.trim().replace(/"/g, ''));
        setColumns(headers);
      }
    };
    reader.readAsText(selectedFile);
  };

  const handleLaunchEnrichment = () => {
    // TODO: Implement Lusha enrichment API call
    console.log('Launching enrichment with:', {
      file: file?.name,
      columnMapping,
      profile,
    });
    setCurrentStep(2);
  };

  const columnOptions = columns.map((col) => ({ value: col, label: col }));

  return (
    <div>
      {/* Page Title */}
      <h1 className="text-2xl font-semibold text-slate-800 mb-6">{t.title}</h1>

      {/* Stepper */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <Stepper steps={STEPS} currentStep={currentStep} />
      </div>

      {/* Back Button */}
      <button
        onClick={() => currentStep > 1 && setCurrentStep(currentStep - 1)}
        className="flex items-center gap-2 text-teal-600 hover:text-teal-700 mb-6 text-sm font-medium"
      >
        <ArrowLeft size={16} />
        {t.back}
      </button>

      {/* Main Content Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        {/* File Upload Zone */}
        <FileUploadZone
          onFileSelect={handleFileSelect}
          label={t.dropzone}
          className="mb-8"
        />

        {/* Column Mapping Section */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-4">
            {t.columnMapping}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SelectDropdown
              options={columnOptions}
              value={columnMapping.companyName}
              onChange={(value) =>
                setColumnMapping((prev) => ({ ...prev, companyName: value }))
              }
              placeholder={t.companyName}
            />
            <SelectDropdown
              options={columnOptions}
              value={columnMapping.website}
              onChange={(value) =>
                setColumnMapping((prev) => ({ ...prev, website: value }))
              }
              placeholder={t.website}
            />
          </div>
        </div>

        {/* Profile Selection */}
        <div className="mb-8">
          <h3 className="text-sm font-medium text-slate-700 mb-4">
            {t.profile}
          </h3>
          <SelectDropdown
            options={PROFILE_OPTIONS}
            value={profile}
            onChange={setProfile}
          />
        </div>

        {/* Launch Button */}
        <button
          onClick={handleLaunchEnrichment}
          disabled={!file}
          className="w-full py-3 bg-gradient-to-r from-green-500 to-green-400 text-white rounded-lg font-medium hover:from-green-600 hover:to-green-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t.launchEnrichment}
        </button>
      </div>
    </div>
  );
}
