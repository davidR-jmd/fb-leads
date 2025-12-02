/**
 * French translations for the application UI
 * Centralized to follow DRY principle
 */
export const TRANSLATIONS = {
  // Navigation
  nav: {
    dashboard: 'Tableau de bord',
    newSearch: 'Nouvelle Recherche',
    history: 'Historique',
    settings: 'Configuration',
  },

  // Dashboard
  dashboard: {
    title: 'Tableau de bord',
    newCampaign: 'Nouvelle Campagne',
    recentCampaigns: 'Campagnes Recentes',
  },

  // Stats
  stats: {
    contactsFoundThisMonth: 'Contacts Trouves ce Mois',
    lushaSuccessRate: 'Taux de Succes Lusha',
    inesSyncedContacts: 'Contacts Synchronises INES',
  },

  // Table headers
  table: {
    campaign: 'Campagne',
    date: 'Date',
    contact: 'Contact',
    successRate: 'Taux de Succes',
    contactsFound: 'Contacts Trouves',
  },

  // Pages
  pages: {
    newSearch: {
      title: 'Nouvelle Recherche',
      placeholder: 'Page de nouvelle recherche - a implementer',
    },
    history: {
      title: 'Historique',
      placeholder: "Page d'historique - a implementer",
    },
    settings: {
      title: 'Configuration',
      placeholder: 'Page de configuration - a implementer',
    },
  },
} as const;
