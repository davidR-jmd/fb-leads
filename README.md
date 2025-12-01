# FB Leads

Automated contact discovery and CRM synchronization system for FB Performance.

## Overview

This system automates the process of:
- Finding contacts from company lists
- Centralizing results in a simple interface
- Automatically syncing contacts to INES CRM

## Tech Stack

- **Frontend:** React + TypeScript + TailwindCSS
- **Backend:** Python + FastAPI
- **Database:** MongoDB
- **Containerization:** Docker

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────▶│  Python API     │────▶│    MongoDB      │
│   (Frontend)    │     │  (FastAPI)      │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ LinkedIn │ │  Lusha   │ │  Kaspr   │
              └──────────┘ └──────────┘ └──────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   INES CRM      │
                        └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd fb-leads
```

2. Copy the environment file and configure it:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Start the services:
```bash
docker-compose up -d
```

4. Access the application:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **MongoDB UI:** http://localhost:8081

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React web application |
| Backend | 8000 | FastAPI REST API |
| MongoDB | 27017 | Database |
| Mongo Express | 8081 | Database admin UI |

## Features

### Company Management
- Import companies from CSV/Excel files
- Add companies manually
- Trigger contact discovery per company

### Contact Discovery
- Automated search via LinkedIn
- Contact enrichment via Lusha
- Contact enrichment via Kaspr
- Confidence scoring

### Contact Management
- View all discovered contacts
- Validate or reject contacts
- Bulk actions support
- Filter by status/source

### CRM Sync
- Push validated contacts to INES CRM
- Sync history and logs
- Error tracking and retry

## API Endpoints

### Companies
- `GET /api/companies` - List companies
- `POST /api/companies` - Create company
- `POST /api/companies/import` - Import from file
- `POST /api/companies/{id}/process` - Start contact discovery

### Contacts
- `GET /api/contacts` - List contacts
- `GET /api/contacts/stats` - Get statistics
- `POST /api/contacts/{id}/validate` - Validate contact
- `POST /api/contacts/{id}/reject` - Reject contact
- `POST /api/contacts/bulk-validate` - Bulk validate

### Sync
- `POST /api/sync/to-crm` - Sync to INES CRM
- `GET /api/sync/logs` - Get sync history
- `GET /api/sync/status` - Get sync status

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

## Project Structure

```
fb-leads/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Configuration, database
│   │   ├── models/        # MongoDB models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── types/         # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## License

Proprietary - FB Performance
