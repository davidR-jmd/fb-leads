import React from 'react';
import { MoreHorizontal } from 'lucide-react';
import { Campaign } from '../types';
import { TRANSLATIONS } from '../constants/translations';

/**
 * Table header configuration
 * Open/Closed Principle: Easy to add columns without modifying render logic
 */
const TABLE_HEADERS = [
  { key: 'campaign', label: TRANSLATIONS.table.campaign },
  { key: 'date', label: TRANSLATIONS.table.date },
  { key: 'contact', label: TRANSLATIONS.table.contact },
  { key: 'successRate', label: TRANSLATIONS.table.successRate },
  { key: 'contactsFound', label: TRANSLATIONS.table.contactsFound },
  { key: 'actions', label: '' },
] as const;

/**
 * Table row component
 * Single Responsibility: Only renders a single campaign row
 */
interface CampaignRowProps {
  campaign: Campaign;
  onMenuClick?: (id: string) => void;
}

function CampaignRow({ campaign, onMenuClick }: CampaignRowProps) {
  return (
    <tr className="hover:bg-slate-50 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="text-sm font-medium text-slate-800">{campaign.name}</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="text-sm text-slate-600">{campaign.date}</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {campaign.contactLink ? (
          <a
            href={campaign.contactLink}
            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            {campaign.contact}
          </a>
        ) : (
          <span className="text-sm text-blue-600">{campaign.contact}</span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="text-sm text-slate-600">{campaign.successRate}</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="text-sm text-slate-600">{campaign.contactsFound}</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right">
        <button
          onClick={() => onMenuClick?.(campaign.id)}
          className="p-1 hover:bg-slate-100 rounded transition-colors"
          aria-label="Options"
        >
          <MoreHorizontal size={20} className="text-slate-400" />
        </button>
      </td>
    </tr>
  );
}

/**
 * CampaignsTable component
 * Single Responsibility: Handles campaign list display in table format
 * Dependency Inversion: Depends on Campaign interface, not concrete implementation
 */
interface CampaignsTableProps {
  campaigns: Campaign[];
  title?: string;
  onMenuClick?: (campaignId: string) => void;
}

export default function CampaignsTable({
  campaigns,
  title = TRANSLATIONS.dashboard.recentCampaigns,
  onMenuClick,
}: CampaignsTableProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200">
        <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {TABLE_HEADERS.map((header) => (
                <th
                  key={header.key}
                  className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider"
                >
                  {header.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {campaigns.map((campaign) => (
              <CampaignRow
                key={campaign.id}
                campaign={campaign}
                onMenuClick={onMenuClick}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
