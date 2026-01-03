# Local setup notes

## Dependencies to install

- Python 3.11
- Node.js 18+
- Docker + Docker Compose
- Backend Python packages (run `pip install -r backend/requirements.txt`)
- Web JavaScript packages (run `npm install` in `web/`)

## Tests and checks to run locally

### Backend

- `cd backend && ruff check .`
- `cd backend && black --check .`
- `cd backend && pytest`

### Web

- `cd web && npm run lint`
- `cd web && npm run format:check`

## Runtime verification

- `docker-compose up -d`
- `make backend-dev` and hit:
  - `http://localhost:8000/health`
  - `http://localhost:8001/health`
- `make web-dev` and open `http://localhost:3000`
