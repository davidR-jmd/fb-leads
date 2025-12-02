import React from 'react';
import { Plus } from 'lucide-react';
import StatsCard from '../components/StatsCard';
import CampaignsTable from '../components/CampaignsTable';
import { TRANSLATIONS } from '../constants/translations';
import { MOCK_CAMPAIGNS, MOCK_STATS } from '../constants/mockData';

/**
 * Dashboard page component
 * Single Responsibility: Orchestrates dashboard view composition
 * Uses translations for French text (DRY principle)
 */
export default function Dashboard() {
  const handleNewCampaign = () => {
    // TODO: Implement campaign creation
    console.log('Create new campaign');
  };

  const handleCampaignMenu = (campaignId: string) => {
    // TODO: Implement campaign menu
    console.log('Open menu for campaign:', campaignId);
  };

  return (
    <div>
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">
          {TRANSLATIONS.dashboard.title}
        </h1>
        <button
          onClick={handleNewCampaign}
          className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors font-medium"
        >
          <Plus size={20} />
          {TRANSLATIONS.dashboard.newCampaign}
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatsCard
          title={TRANSLATIONS.stats.contactsFoundThisMonth}
          value={MOCK_STATS.contactsFoundThisMonth}
        />
        <StatsCard
          title={TRANSLATIONS.stats.lushaSuccessRate}
          value={`${MOCK_STATS.lushaSuccessRate}%`}
        />
        <StatsCard
          title={TRANSLATIONS.stats.inesSyncedContacts}
          value={MOCK_STATS.inesSyncedContacts}
        />
      </div>

      {/* Campaigns Table */}
      <CampaignsTable
        campaigns={MOCK_CAMPAIGNS}
        onMenuClick={handleCampaignMenu}
      />
    </div>
  );
}
