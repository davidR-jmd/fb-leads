import { Campaign, DashboardStats } from '../types';

/**
 * Mock data for development
 * Separated from components for better testability and maintainability
 */
export const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: '1',
    name: 'Process Ltd 1',
    date: '12/10/2022',
    contact: 'Crasse',
    contactLink: '#',
    successRate: 450,
    contactsFound: 0,
  },
  {
    id: '2',
    name: 'Campagne Lalen 2',
    date: '09/10/2022',
    contact: 'Crasse',
    contactLink: '#',
    successRate: 450,
    contactsFound: 0,
  },
  {
    id: '3',
    name: 'Process Ltd 3',
    date: '19/10/2022',
    contact: 'Crasse',
    contactLink: '#',
    successRate: 149,
    contactsFound: 0,
  },
  {
    id: '4',
    name: 'Campagne Lalen 4',
    date: '18/10/2022',
    contact: 'Crasse',
    contactLink: '#',
    successRate: 420,
    contactsFound: 0,
  },
  {
    id: '5',
    name: 'Campagne Laien 5',
    date: '18/10/2022',
    contact: 'Crasse',
    contactLink: '#',
    successRate: 140,
    contactsFound: 0,
  },
];

export const MOCK_STATS: DashboardStats = {
  contactsFoundThisMonth: 450,
  lushaSuccessRate: 85,
  inesSyncedContacts: 420,
};
