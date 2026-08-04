# Jira Dashboard v2.0

A modern, full-featured Jira dashboard for the ADAS Platform team. Built with FastAPI + Next.js.

## Features

- **Multi-project support** — Switch between Jira projects dynamically
- **Dashboard** — Stats cards, status charts, assignee workload breakdown
- **Kanban Board** — Drag-and-drop issue cards across status columns
- **Sprint Views** — Sprint selector, progress bar, sprint-filtered boards
- **Analytics** — Burndown charts, velocity tracking, issue trends
- **Real-time Updates** — WebSocket-powered live refresh when issues change
- **Dark Mode** — Toggle between light and dark themes
- **Keyboard Shortcuts** — Ctrl+K for search, / for quick focus
- **Responsive** — Works on desktop and tablet

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Jira API token ([generate here](https://id.atlassian.com/manage-profile/security/api-tokens))

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your credentials

# Start server
uvicorn app.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Docker (Full Stack)

```bash
# Edit backend/.env with your credentials first
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture

```
├── backend/           FastAPI + httpx async Jira client
│   ├── app/api/       REST endpoints + WebSocket
│   ├── app/services/  Jira client, caching, sync, analytics
│   ├── app/models/    Pydantic response models
│   └── app/core/      Mapper, pagination, exceptions
│
├── frontend/          Next.js 16 + TypeScript + Tailwind
│   ├── src/app/       App Router pages
│   ├── src/components/ React components
│   ├── src/hooks/     TanStack Query hooks
│   ├── src/store/     Zustand state management
│   └── src/lib/       API client, types, utilities
│
└── docker-compose.yml  Full stack orchestration
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET /api/projects | List accessible projects |
| GET /api/projects/{key}/issues | Paginated issues with filters |
| GET /api/boards | List boards |
| GET /api/boards/{id}/issues | Board issues grouped by status |
| GET /api/boards/{id}/sprints | Sprints for a board |
| GET /api/analytics/overview/{key} | Project analytics overview |
| GET /api/analytics/burndown | Sprint burndown data |
| GET /api/analytics/velocity | Velocity across sprints |
| GET /api/analytics/trends | Created vs resolved trends |
| WS /ws/updates | Real-time issue change notifications |

## Configuration

All config via environment variables (see `backend/.env.example`):

| Variable | Description |
|----------|-------------|
| JIRA_BASE_URL | Atlassian instance URL |
| JIRA_USER_EMAIL | Account email |
| JIRA_API_TOKEN | API token |
| CACHE_TTL_SECONDS | Cache duration (default: 300) |
| SYNC_INTERVAL_SECONDS | Poll interval for live updates (default: 60) |
