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
