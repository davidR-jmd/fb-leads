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
    linkedin: {
      title: 'Configuration LinkedIn',
      search: 'Recherche LinkedIn',
      status: 'Statut',
      statusLabels: {
        disconnected: 'Déconnecté',
        connecting: 'Connexion en cours...',
        need_email_code: 'Code de vérification requis',
        need_manual_login: 'Connexion manuelle requise',
        awaiting_manual_login: 'En attente de connexion manuelle',
        connected: 'Connecté',
        busy: 'Occupé',
        error: 'Erreur',
      },
      authMethodLabels: {
        cookie: 'Cookie',
        credentials: 'Identifiants',
        manual: 'Manuel',
      },
      cookieAuth: {
        title: 'Connexion par Cookie (Recommandé)',
        description: 'Collez votre cookie li_at LinkedIn pour une connexion fiable.',
        howToGet: 'Comment obtenir le cookie ?',
        howToGetSteps: [
          '1. Connectez-vous à LinkedIn dans votre navigateur',
          '2. Ouvrez les DevTools (F12) > Application > Cookies',
          '3. Trouvez le cookie "li_at" sur linkedin.com',
          '4. Copiez sa valeur et collez-la ci-dessous',
        ],
        placeholder: 'Collez votre cookie li_at ici...',
        connect: 'Connecter avec le cookie',
      },
      manualAuth: {
        title: 'Connexion Manuelle (Fallback)',
        description: 'Si le cookie ne fonctionne pas, ouvrez un navigateur visible pour vous connecter manuellement.',
        openBrowser: 'Ouvrir le navigateur',
        waitingMessage: 'Connectez-vous dans la fenêtre du navigateur, puis cliquez sur "Valider la session".',
        validateSession: 'Valider la session',
      },
      email: 'Email LinkedIn',
      password: 'Mot de passe',
      connect: 'Se connecter',
      disconnect: 'Se déconnecter',
      lastConnected: 'Dernière connexion',
      account: 'Compte',
      verifyTitle: 'Vérification requise',
      verifyMessage: 'LinkedIn a envoyé un code de vérification à votre adresse email.',
      verifyCode: 'Code de vérification',
      verifySubmit: 'Valider',
      cancel: 'Annuler',
      searchPlaceholder: 'Ex: Marketing Director Paris',
      searchButton: 'Rechercher',
      resultsCount: 'contacts trouvés',
      noResults: 'Aucun résultat trouvé',
      notConnected: 'LinkedIn non connecté. Contactez un administrateur.',
      contactName: 'Nom',
      contactTitle: 'Poste',
      contactCompany: 'Entreprise',
      contactLocation: 'Localisation',
      viewProfile: 'Voir le profil',
    },
  },

  // Navigation (extended)
  navExtended: {
    linkedin: 'LinkedIn',
    prospects: 'Prospect Finder',
  },
} as const;
