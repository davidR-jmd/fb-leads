/**
 * Campaign entity type
 * Single Responsibility: Only defines the Campaign data structure
 */
export interface Campaign {
  id: string;
  name: string;
  date: string;
  contact: string;
  contactLink?: string;
  successRate: number;
  contactsFound: number;
}

/**
 * Dashboard statistics type
 */
export interface DashboardStats {
  contactsFoundThisMonth: number;
  lushaSuccessRate: number;
  inesSyncedContacts: number;
}
