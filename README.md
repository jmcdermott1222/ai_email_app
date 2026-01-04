# AI Email Copilot

This repository contains a minimal monorepo scaffold for the AI Email + Calendar Copilot.
It includes a FastAPI backend (API + worker) and a Next.js web frontend.

## Prerequisites

- Python 3.11
- Node.js 18+
- Docker + Docker Compose

## Initial Setup

1. Copy environment variables:

```bash
cp .env.example .env
```

Fill in the OAuth and security values in `.env`:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI` (default: `http://localhost:8000/auth/google/callback`)
- `SESSION_JWT_SECRET`
- `ENCRYPTION_KEY` (Fernet base64 key, generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `DATABASE_URL` (optional override)
- `WEB_BASE_URL` (default: `http://localhost:3000`)
- `API_BASE_URL` (default: `http://localhost:8000`)

2. Start Postgres:

```bash
docker-compose up -d
```

3. Backend dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Web dependencies:

```bash
cd web
npm install
```

## Development

### Backend (API + Worker)

```bash
make backend-dev
```

- API: http://localhost:8000/health
- Worker: http://localhost:8001/health

### Web

```bash
make web-dev
```

- Web: http://localhost:3000
- Login: http://localhost:3000/login
- Dashboard: http://localhost:3000/dashboard

### Google OAuth Flow

- Start OAuth: `http://localhost:8000/auth/google/start`
- Callback: `http://localhost:8000/auth/google/callback`
- Integration status (requires session cookie): `http://localhost:8000/api/integrations/google/status`
- Preferences (requires session cookie): `http://localhost:8000/api/preferences`
- Manual Gmail sync (requires session cookie): `POST http://localhost:8000/api/sync/full`
- Emails (requires session cookie): `http://localhost:8000/api/emails`
- Attachment processing (requires session cookie): `POST http://localhost:8000/api/emails/{id}/attachments/process`
- Triage (requires session cookie): `POST http://localhost:8000/api/emails/{id}/triage`
- Feedback (requires session cookie): `POST http://localhost:8000/api/emails/{id}/feedback`
- Manual actions (requires session cookie): `POST http://localhost:8000/api/emails/{id}/actions`
- Automation run (requires session cookie): `POST http://localhost:8000/api/automation/run_for_email/{id}`
- Audit log (requires session cookie): `GET http://localhost:8000/api/audit`
- Snooze sweep (worker): `POST http://localhost:8001/internal/jobs/snooze_sweep`

## Common Commands

```bash
make dev       # start postgres
make lint      # run backend + web linters
make format    # format backend + web
make test      # run backend tests + web lint
make migrate   # apply alembic migrations
```

## Notes

- The backend uses FastAPI with SQLAlchemy 2.x and Alembic.
- The web app is a minimal Next.js (App Router) scaffold with placeholder pages.
- The API base URL is configured via `NEXT_PUBLIC_API_BASE_URL` in `.env`.
