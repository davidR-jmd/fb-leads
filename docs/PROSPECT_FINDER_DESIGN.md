# Prospect Finder - Design Document

> Application de recherche de prospects B2B pour le marche francais

## Table of Contents

1. [Overview](#overview)
2. [Functional Requirements](#functional-requirements)
3. [Architecture](#architecture)
4. [Data Models](#data-models)
5. [API Design](#api-design)
6. [External Services Integration](#external-services-integration)
7. [Rate Limits & Quotas](#rate-limits--quotas)
8. [Cost Estimation](#cost-estimation)
9. [UI/UX Design](#uiux-design)
10. [Implementation Plan](#implementation-plan)

---

## Overview

### Purpose

Automate the prospect discovery process for French B2B companies. The application finds decision-makers based on job function and optional company criteria, providing LinkedIn profile URLs ready for manual enrichment via Lusha Chrome plugin.

### Target Users

- Small sales teams
- Business development professionals
- Previously using manual LinkedIn searches

### Key Constraints

- **Job function is MANDATORY** for all searches
- Lusha enrichment is **manual** (Chrome plugin, not API)
- Focus on **French companies only**
- Support both **manual search** and **Excel import**

### Integration with Existing App

This is a **NEW feature** added alongside existing functionality:

| Existing Page | New Page |
|---------------|----------|
| `/recherche` - LinkedIn Search (Excel + Keywords) | `/prospects` - Prospect Finder (Pappers + Google) |
| Uses LinkedIn directly | Uses Pappers + Google Search API |
| Requires LinkedIn connection | No LinkedIn connection needed |
| Rate limited by LinkedIn | Rate limited by Pappers/Google |

**Navigation Structure:**

```
Sidebar Menu:
├── Nouvelle Recherche (existing LinkedIn search)
├── Prospect Finder (NEW - this feature)
├── Historique
├── Configuration
└── Admin
    ├── Utilisateurs
    └── LinkedIn
```

---

## Functional Requirements

### FR-1: Search Modes

| Mode | Description |
|------|-------------|
| **Manual Search** | User enters job function + optional filters |
| **Excel Import** | User uploads company list + job function |

### FR-2: Search Criteria

| Criterion | Required | Type | Description |
|-----------|----------|------|-------------|
| `job_function` | **YES** | string | Target job title (e.g., "Directeur Commercial") |
| `company_name` | No | string | Specific company to search |
| `departements` | No | string[] | French department codes (e.g., ["69", "75"]) |
| `size_min` | No | int | Minimum employee count |
| `size_max` | No | int | Maximum employee count |
| `revenue_min` | No | int | Minimum revenue in euros |
| `revenue_max` | No | int | Maximum revenue in euros |
| `industry_naf` | No | string | NAF/APE industry code |
| `is_public` | No | bool | Public (SA) vs Private (SAS/SARL) |

### FR-3: Excel Import

- Accept `.xlsx` and `.csv` files
- Auto-detect column mapping:
  - Company name
  - SIREN/SIRET
  - Location
  - Custom columns (preserved in output)
- Enrich with Pappers data
- Find LinkedIn profiles for specified job function

### FR-4: Output

| Field | Source | Description |
|-------|--------|-------------|
| `company_name` | Pappers/Excel | Company legal name |
| `siren` | Pappers | SIREN identifier |
| `siret` | Pappers | SIRET (if establishment) |
| `revenue` | Pappers | Chiffre d'affaires |
| `employees` | Pappers | Effectif |
| `address` | Pappers | Siege social |
| `naf_code` | Pappers | Industry code |
| `legal_form` | Pappers | SAS, SARL, SA, etc. |
| `contact_name` | Google/LinkedIn | Prospect name |
| `contact_title` | Google/LinkedIn | Job title |
| `linkedin_url` | Google Search | Profile URL for Lusha |

### FR-5: Export

- Export results as Excel (`.xlsx`)
- Export results as CSV
- Copy LinkedIn URLs to clipboard (bulk)

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│                     (React/Next.js)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Search    │  │   Excel     │  │      Results           │ │
│  │    Form     │  │   Import    │  │      Table             │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND                                   │
│                    (FastAPI/Python)                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    API Layer                             │   │
│  │  POST /api/prospects/search                              │   │
│  │  POST /api/prospects/import                              │   │
│  │  GET  /api/prospects/export/{job_id}                     │   │
│  │  GET  /api/search/status/{job_id}                        │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                   │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │                  Service Layer                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │  Prospect   │  │   Excel     │  │    Search       │  │   │
│  │  │  Service    │  │   Parser    │  │    Orchestrator │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                   │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │                External API Clients                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │  Pappers    │  │   Google    │  │    SIRENE       │  │   │
│  │  │  Client     │  │   Search    │  │    Client       │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Rate Limiter                            │   │
│  │            (Per API, shared across requests)             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE                                  │
│                       (MongoDB)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Search    │  │   Rate      │  │      Company            │ │
│  │   Jobs      │  │   Limits    │  │      Cache              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Search Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     SEARCH ORCHESTRATOR                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Job Function   │
                    │   (REQUIRED)    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  Manual Search  │           │  Excel Import   │
    └────────┬────────┘           └────────┬────────┘
             │                             │
             ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  Has company    │           │  Parse Excel    │
    │  name?          │           │  Detect columns │
    └────────┬────────┘           └────────┬────────┘
             │                             │
      ┌──────┴──────┐                      │
      ▼             ▼                      │
┌──────────┐  ┌──────────┐                │
│   YES    │  │    NO    │                │
│ Pappers  │  │ Pappers  │                │
│ by name  │  │ by filter│                │
└────┬─────┘  └────┬─────┘                │
     │             │                       │
     └──────┬──────┘                       │
            │                              │
            ▼                              ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  Company List   │           │  Company List   │
    │  (with SIREN,   │           │  (from Excel +  │
    │   revenue...)   │           │   Pappers)      │
    └────────┬────────┘           └────────┬────────┘
             │                             │
             └──────────────┬──────────────┘
                            ▼
                  ┌─────────────────┐
                  │  For each       │
                  │  company:       │
                  │                 │
                  │  Google Search  │
                  │  "{function}"   │
                  │  "{company}"    │
                  │  site:linkedin  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Extract:       │
                  │  - Name         │
                  │  - LinkedIn URL │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  OUTPUT         │
                  │                 │
                  │  Company +      │
                  │  Contact +      │
                  │  LinkedIn URL   │
                  │                 │
                  │  → Lusha        │
                  └─────────────────┘
```

---

## Data Models

### Database Collections (MongoDB)

#### `search_jobs`

```typescript
interface SearchJob {
  _id: ObjectId;

  // Search parameters
  job_function: string;           // Required
  mode: "manual" | "excel_import";

  // Manual search filters (optional)
  filters?: {
    company_name?: string;
    departements?: string[];
    size_min?: number;
    size_max?: number;
    revenue_min?: number;
    revenue_max?: number;
    industry_naf?: string;
    is_public?: boolean;
  };

  // Excel import
  excel_file_id?: ObjectId;       // GridFS reference
  column_mapping?: {
    company_name?: string;
    siren?: string;
    [key: string]: string;
  };

  // Status
  status: "pending" | "processing" | "completed" | "failed";
  progress: {
    total_companies: number;
    processed: number;
    found: number;
    errors: number;
  };

  // Results
  results: ProspectResult[];

  // Metadata
  created_at: Date;
  updated_at: Date;
  created_by?: string;
}
```

#### `prospect_results`

```typescript
interface ProspectResult {
  _id: ObjectId;
  job_id: ObjectId;

  // Company data (Pappers)
  company: {
    name: string;
    siren?: string;
    siret?: string;
    revenue?: number;
    employees?: number;
    address?: {
      street?: string;
      city?: string;
      postal_code?: string;
    };
    naf_code?: string;
    naf_label?: string;
    legal_form?: string;
    creation_date?: Date;
  };

  // Contact data (Google Search)
  contact?: {
    name?: string;
    title?: string;
    linkedin_url?: string;
  };

  // Search metadata
  searched_function: string;
  source: "pappers" | "excel" | "google";

  // Status
  linkedin_found: boolean;
  enriched_with_lusha: boolean;   // Manual flag

  created_at: Date;
}
```

#### `company_cache`

```typescript
interface CompanyCache {
  _id: string;                    // SIREN as ID

  // Pappers data
  name: string;
  siren: string;
  siret_siege: string;
  revenue?: number;
  employees?: number;
  address?: object;
  naf_code?: string;
  legal_form?: string;
  dirigeants?: Dirigeant[];

  // Cache metadata
  fetched_at: Date;
  expires_at: Date;               // TTL: 30 days
}
```

#### `rate_limits`

```typescript
interface RateLimitState {
  _id: string;                    // API name

  // Counters
  requests_today: number;
  requests_this_hour: number;
  requests_this_minute: number;

  // Timestamps
  day_started: Date;
  hour_started: Date;
  minute_started: Date;
  last_request: Date;

  // Cooldown
  cooldown_until?: Date;
}
```

---

## API Design

### Endpoints

#### POST `/api/prospects/search`

Start a new prospect search (manual mode).

**Request:**
```json
{
  "job_function": "Directeur Commercial",
  "filters": {
    "company_name": "Carrefour",
    "departements": ["69", "75"],
    "size_min": 50,
    "size_max": 500,
    "revenue_min": 1000000,
    "revenue_max": null,
    "industry_naf": "62.01Z",
    "is_public": false
  }
}
```

**Response:**
```json
{
  "job_id": "65a1b2c3d4e5f6789",
  "status": "processing",
  "estimated_companies": 150,
  "message": "Search started"
}
```

#### POST `/api/prospects/import`

Start a prospect search from Excel file.

**Request:** `multipart/form-data`
- `file`: Excel/CSV file
- `job_function`: string (required)
- `column_mapping`: JSON (optional, auto-detected if not provided)

**Response:**
```json
{
  "job_id": "65a1b2c3d4e5f6790",
  "status": "processing",
  "companies_detected": 87,
  "column_mapping": {
    "company_name": "Société",
    "siren": "SIREN"
  }
}
```

#### GET `/api/prospects/search/{job_id}`

Get search job status and results.

**Response:**
```json
{
  "job_id": "65a1b2c3d4e5f6789",
  "status": "completed",
  "progress": {
    "total_companies": 150,
    "processed": 150,
    "found": 127,
    "errors": 3
  },
  "results": [
    {
      "company": {
        "name": "Carrefour",
        "siren": "652014051",
        "revenue": 82600000000,
        "employees": 150000,
        "naf_code": "47.11F",
        "legal_form": "SA"
      },
      "contact": {
        "name": "Jean Dupont",
        "title": "Directeur Commercial France",
        "linkedin_url": "https://linkedin.com/in/jean-dupont-123"
      },
      "searched_function": "Directeur Commercial",
      "linkedin_found": true
    }
  ]
}
```

#### GET `/api/prospects/export/{job_id}`

Export results as Excel/CSV.

**Query params:**
- `format`: `xlsx` | `csv` (default: `xlsx`)

**Response:** File download

#### GET `/api/rate-limits/status`

Get current rate limit status for all APIs.

**Response:**
```json
{
  "pappers": {
    "requests_today": 45,
    "limit_today": 1000,
    "requests_remaining": 955,
    "cooldown_until": null
  },
  "google_search": {
    "requests_today": 89,
    "limit_today": 100,
    "requests_remaining": 11,
    "cooldown_until": null
  }
}
```

#### POST `/api/company/lookup`

Single company lookup (for autocomplete/validation).

**Request:**
```json
{
  "query": "Carrefour",
  "by": "name"
}
```

**Response:**
```json
{
  "companies": [
    {
      "name": "CARREFOUR SA",
      "siren": "652014051",
      "revenue": 82600000000,
      "employees": 150000,
      "address": "93 Avenue de Paris, 91300 Massy"
    }
  ]
}
```

---

## External Services Integration

### Pappers API

**Purpose:** French company data (discovery + enrichment)

**Base URL:** `https://api.pappers.fr/v2`

**Endpoints used:**

| Endpoint | Purpose | Cost |
|----------|---------|------|
| `GET /recherche` | Search companies by criteria | 1 credit |
| `GET /entreprise` | Get company by SIREN | 1 credit |
| `GET /dirigeants` | Get company directors | 1 credit |

**Example - Search companies:**
```http
GET /recherche?api_token=xxx
  &departement=69
  &effectif_min=50
  &effectif_max=200
  &chiffre_affaires_min=1000000
  &code_naf=62.01Z
```

**Response fields used:**
```json
{
  "resultats": [
    {
      "siren": "123456789",
      "nom_entreprise": "ACME SAS",
      "siege": {
        "adresse": "...",
        "code_postal": "69001",
        "ville": "LYON"
      },
      "effectif": "50 a 99 salaries",
      "chiffre_affaires": 5000000,
      "code_naf": "62.01Z",
      "libelle_code_naf": "Programmation informatique",
      "forme_juridique": "SAS",
      "dirigeants": [
        {
          "nom": "DUPONT",
          "prenom": "Jean",
          "fonction": "President"
        }
      ]
    }
  ]
}
```

### Google Custom Search API

**Purpose:** Find LinkedIn profile URLs

**Base URL:** `https://www.googleapis.com/customsearch/v1`

**Configuration:**
- Create Custom Search Engine (CSE) at https://cse.google.com
- Restrict to `linkedin.com/in/*`

**Example request:**
```http
GET /customsearch/v1
  ?key=xxx
  &cx=your-cse-id
  &q=Directeur Commercial "Carrefour" site:linkedin.com/in
  &num=3
```

**Response parsing:**
```json
{
  "items": [
    {
      "title": "Jean Dupont - Directeur Commercial - Carrefour | LinkedIn",
      "link": "https://www.linkedin.com/in/jean-dupont-123",
      "snippet": "View Jean Dupont's profile on LinkedIn..."
    }
  ]
}
```

**Name extraction from title:**
```python
def extract_name_from_title(title: str) -> str:
    # "Jean Dupont - Directeur Commercial - Carrefour | LinkedIn"
    # → "Jean Dupont"
    return title.split(" - ")[0].strip()
```

### INSEE SIRENE API (Optional - Free)

**Purpose:** Basic company discovery (free alternative to Pappers)

**Base URL:** `https://api.insee.fr/entreprises/sirene/V3`

**Limitations:**
- No revenue data
- No directors
- Employee count as ranges only

**Use case:** Initial broad discovery, then enrich with Pappers

---

## Rate Limits & Quotas

### Rate Limit Configuration

```python
RATE_LIMITS = {
    "pappers": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "requests_per_day": 1000,        # Based on plan
        "min_delay_ms": 200,
        "cooldown_minutes": 5,
    },
    "google_search": {
        "requests_per_minute": 10,
        "requests_per_hour": 60,
        "requests_per_day": 100,          # Free tier
        "min_delay_ms": 1000,
        "cooldown_minutes": 60,           # Wait if limit hit
    },
    "sirene": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "requests_per_day": 10000,
        "min_delay_ms": 2000,             # Required by INSEE
        "cooldown_minutes": 1,
    },
}
```

### Rate Limiter Implementation

```python
class MultiAPIRateLimiter:
    """
    Unified rate limiter for all external APIs.
    """

    async def can_request(self, api: str) -> tuple[bool, str | None]:
        """Check if request is allowed."""
        ...

    async def record_request(self, api: str) -> None:
        """Record a successful request."""
        ...

    async def get_delay(self, api: str) -> float:
        """Get required delay before next request."""
        ...

    async def wait_if_needed(self, api: str) -> None:
        """Wait for rate limit if necessary."""
        ...
```

### Quota Management UI

Display remaining quotas to user:

```
┌─────────────────────────────────────────────────────┐
│  Quotas restants aujourd'hui                        │
├─────────────────────────────────────────────────────┤
│  Pappers:        ████████░░  450/500 recherches    │
│  Google Search:  ██░░░░░░░░   23/100 recherches    │
│  SIRENE:         ██████████  Illimite              │
└─────────────────────────────────────────────────────┘
```

---

## Cost Estimation

### Per-API Costs

| API | Free Tier | Paid Plan | Cost/Request |
|-----|-----------|-----------|--------------|
| Pappers | 0 | 49-199/month | ~0.05-0.10 |
| Google Search | 100/day | $5/1000 | ~$0.005 |
| SIRENE | Unlimited | Free | 0 |

### Monthly Cost Scenarios

#### Scenario A: 100 prospects/month (Light usage)

| Item | Quantity | Cost |
|------|----------|------|
| Pappers | ~150 requests | 49 (starter plan) |
| Google Search | ~150 requests | 0 (free tier) |
| **Total** | | **~49/month** |

#### Scenario B: 500 prospects/month (Medium usage)

| Item | Quantity | Cost |
|------|----------|------|
| Pappers | ~750 requests | 99/month |
| Google Search | ~750 requests | ~$3 |
| **Total** | | **~105/month** |

#### Scenario C: 2000 prospects/month (Heavy usage)

| Item | Quantity | Cost |
|------|----------|------|
| Pappers | ~3000 requests | 199/month |
| Google Search | ~3000 requests | ~$15 |
| **Total** | | **~220/month** |

### Cost Optimization Strategies

1. **Cache company data** (30-day TTL)
2. **Use SIRENE first** (free), Pappers for enrichment
3. **Batch requests** where possible
4. **Skip companies without online presence**

---

## UI/UX Design

### Main Search Page

```
┌─────────────────────────────────────────────────────────────────┐
│  ◀ Prospects                                     [? Aide]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔍 Recherche de Prospects                                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Fonction *                                              │   │
│  │  [Directeur Commercial                              ▼]   │   │
│  │                                                          │   │
│  │  Suggestions: Directeur Commercial, DRH, DSI, DAF, CEO   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                 │
│   [📝 Recherche Manuelle]    [📁 Import Excel]                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ RECHERCHE MANUELLE ─────────────────────────────────────┐  │
│  │                                                           │  │
│  │  Entreprise (optionnel)                                   │  │
│  │  [                                                    ]   │  │
│  │                                                           │  │
│  │  ┌─ Filtres entreprise ────────────────────────────────┐ │  │
│  │  │                                                      │ │  │
│  │  │  Departement                                         │ │  │
│  │  │  [☑ 69 Rhone] [☑ 75 Paris] [☐ 13 BdR] [+ Ajouter]  │ │  │
│  │  │                                                      │ │  │
│  │  │  Effectif                                            │ │  │
│  │  │  [50      ] a [200     ] salaries                   │ │  │
│  │  │                                                      │ │  │
│  │  │  Chiffre d'affaires                                  │ │  │
│  │  │  [1 000 000] a [         ] euros                    │ │  │
│  │  │                                                      │ │  │
│  │  │  Secteur d'activite                                  │ │  │
│  │  │  [Tous les secteurs                             ▼]  │ │  │
│  │  │                                                      │ │  │
│  │  │  Type d'entreprise                                   │ │  │
│  │  │  (●) Toutes  ( ) Privees  ( ) Publiques             │ │  │
│  │  │                                                      │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ IMPORT EXCEL ───────────────────────────────────────────┐  │
│  │                                                           │  │
│  │   ┌─────────────────────────────────────────────────┐    │  │
│  │   │                                                 │    │  │
│  │   │     📎 Glisser un fichier Excel (.xlsx, .csv)  │    │  │
│  │   │                                                 │    │  │
│  │   │              ou [Parcourir...]                  │    │  │
│  │   │                                                 │    │  │
│  │   └─────────────────────────────────────────────────┘    │  │
│  │                                                           │  │
│  │   Fichier: companies.xlsx (87 lignes)         [✕ Retirer]│  │
│  │                                                           │  │
│  │   Mapping des colonnes:                                   │  │
│  │   ┌─────────────┬─────────────────────┐                  │  │
│  │   │ Colonne     │ Correspondance      │                  │  │
│  │   ├─────────────┼─────────────────────┤                  │  │
│  │   │ "Societe"   │ [Nom entreprise  ▼] │                  │  │
│  │   │ "N_SIREN"   │ [SIREN          ▼] │                  │  │
│  │   │ "Ville"     │ [Ignorer        ▼] │                  │  │
│  │   └─────────────┴─────────────────────┘                  │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│                                                                 │
│   Quotas: Pappers 450/500 | Google 23/100                      │
│                                                                 │
│                    [🔎 Lancer la recherche]                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Results Page

```
┌─────────────────────────────────────────────────────────────────┐
│  ◀ Retour                                    Recherche #1234   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Fonction: Directeur Commercial                                 │
│  Filtres: Rhone (69), 50-200 salaries, CA > 1M                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ████████████████████░░░░  127/150 traites             │   │
│  │  ✓ 98 profils LinkedIn trouves                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [📥 Exporter Excel]  [📋 Copier URLs LinkedIn]  [🔄 Refresh] │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☑ │ Entreprise      │ CA      │ Eff. │ Contact         │   │
│  ├───┼─────────────────┼─────────┼──────┼─────────────────┤   │
│  │ ☑ │ ACME SAS        │ 5.2M    │ 87   │ J. Dupont       │   │
│  │   │ Lyon 69001      │         │      │ Dir. Commercial  │   │
│  │   │                 │         │      │ [🔗 LinkedIn]    │   │
│  ├───┼─────────────────┼─────────┼──────┼─────────────────┤   │
│  │ ☑ │ XYZ SARL        │ 2.1M    │ 52   │ M. Martin       │   │
│  │   │ Villeurbanne    │         │      │ Directrice Com.  │   │
│  │   │                 │         │      │ [🔗 LinkedIn]    │   │
│  ├───┼─────────────────┼─────────┼──────┼─────────────────┤   │
│  │ ☐ │ ABC SA          │ 12.5M   │ 180  │ Non trouve      │   │
│  │   │ Lyon 69003      │         │      │ [🔍 Rechercher]  │   │
│  └───┴─────────────────┴─────────┴──────┴─────────────────┘   │
│                                                                 │
│  Affichage 1-25 sur 127      [< Precedent] [Suivant >]        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow for User

```
1. User selects job function (required)
           │
           ▼
2. User either:
   ├── Enters manual filters (optional)
   └── Uploads Excel file
           │
           ▼
3. Click "Lancer la recherche"
           │
           ▼
4. Progress bar shows status
           │
           ▼
5. Results displayed in table
   - Company info (Pappers)
   - Contact name (Google)
   - LinkedIn URL (clickable)
           │
           ▼
6. User clicks LinkedIn URL
   → Opens in new tab
   → Uses Lusha Chrome plugin
   → Gets phone/email
           │
           ▼
7. User exports results to Excel
   (for CRM import)
```

---

## Implementation Plan

### Phase 1: Core Backend (Week 1)

- [ ] Set up FastAPI project structure
- [ ] Implement Pappers API client
- [ ] Implement Google Custom Search client
- [ ] Create rate limiter for both APIs
- [ ] Implement company cache (MongoDB)
- [ ] Create search orchestrator service
- [ ] Add basic API endpoints

### Phase 2: Search Features (Week 2)

- [ ] Manual search with all filters
- [ ] Excel file parsing
- [ ] Column auto-detection
- [ ] Async job processing
- [ ] Progress tracking
- [ ] Results storage

### Phase 3: Frontend (Week 3)

- [ ] Search form with function selector
- [ ] Filter inputs (optional fields)
- [ ] Excel drag & drop upload
- [ ] Column mapping UI
- [ ] Results table with pagination
- [ ] LinkedIn URL buttons
- [ ] Export functionality

### Phase 4: Polish & Optimization (Week 4)

- [ ] Company name autocomplete
- [ ] Bulk LinkedIn URL copy
- [ ] Quota display
- [ ] Error handling & retry logic
- [ ] Caching optimization
- [ ] Performance testing

---

## Appendix

### A. NAF Codes (Common)

| Code | Label |
|------|-------|
| 62.01Z | Programmation informatique |
| 62.02A | Conseil en systemes informatiques |
| 70.22Z | Conseil en gestion |
| 64.19Z | Autres intermediations monetaires |
| 47.11F | Hypermarches |
| 46.90Z | Commerce de gros non specialise |

### B. French Departments

| Code | Name |
|------|------|
| 75 | Paris |
| 69 | Rhone |
| 13 | Bouches-du-Rhone |
| 31 | Haute-Garonne |
| 33 | Gironde |
| 59 | Nord |
| 67 | Bas-Rhin |
| 92 | Hauts-de-Seine |
| 93 | Seine-Saint-Denis |
| 94 | Val-de-Marne |

### C. Legal Forms

| Code | Label | Type |
|------|-------|------|
| SAS | Societe par Actions Simplifiee | Private |
| SARL | Societe a Responsabilite Limitee | Private |
| SA | Societe Anonyme | Public |
| EURL | Entreprise Unipersonnelle | Private |
| SCI | Societe Civile Immobiliere | Private |

### D. Error Codes

| Code | Message | Action |
|------|---------|--------|
| `RATE_LIMIT_EXCEEDED` | Quota depasse | Wait or upgrade |
| `COMPANY_NOT_FOUND` | Entreprise non trouvee | Check SIREN/name |
| `LINKEDIN_NOT_FOUND` | Profil LinkedIn non trouve | Manual search |
| `INVALID_FILE` | Format de fichier invalide | Use .xlsx or .csv |
| `MISSING_FUNCTION` | Fonction obligatoire | Add job function |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-XX-XX | Initial design document |
