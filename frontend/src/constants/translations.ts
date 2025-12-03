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
      title: 'Import & Recherche',
      steps: {
        import: 'Import',
        validation: 'Validation',
        synchronisation: 'Synchronisation',
      },
      back: 'Retour',
      dropzone: 'Drag on-drop et une mappier en Excel/CSV',
      columnMapping: 'Mapperment des colomnes',
      companyName: "Nom de l'entreprise",
      website: 'Site Web',
      profile: 'Profil',
      profiles: {
        marketingDirector: 'Directeur Marketing',
        salesDirector: 'Directeur Commercial',
        ceo: 'PDG / CEO',
        cto: 'CTO / Directeur Technique',
        hr: 'DRH / Ressources Humaines',
      },
      launchEnrichment: "Lancer l'enrichissement via Lusha",
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
