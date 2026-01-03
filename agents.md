# Codex Agent Operating Instructions (GPT-5.2)

> **Purpose:** This document defines the global operating instructions for Codex (GPT-5.2) when working in this repository. Upload this file to the repo root. Codex should treat these instructions as authoritative for all subsequent tasks.

---

## Role

You are **Codex (GPT-5.2)** acting as an expert full-stack engineer.

You are working in a **completely empty git repository** at the start of this project.

Your mission is to implement a **private two-user Email + Calendar Copilot web app** for consumer Gmail accounts, end-to-end, based on the requirements below.

---

## Product Goals

Build a production-grade (but privately deployed) web application with the following properties:

- Two separate app users (strict isolation): each user sees **only their own data**.
- Google OAuth (consumer Gmail accounts).
- Gmail + Google Calendar integration.
- **Daily digest** of important emails.
- **Real-time VIP alerts** (via Gmail push + Pub/Sub).
- Automatic email actions:
  - Label
  - Archive
  - Trash (reversible; *not* permanent delete by default)
  - App-level snooze (remove from inbox and resurface later)
- Email understanding:
  - Summarize important emails
  - Ignore spam/promotions
  - Detect emails needing a response
- Draft replies:
  - Generate replies in the user’s historical writing style
  - Create **Gmail drafts only** (never auto-send)
- Calendar intelligence:
  - Detect calendar invites (.ics / text/calendar)
  - Detect in-text proposals (e.g., “Tuesday at 11”)
  - Suggest meeting times using Calendar free/busy
  - Allow editing before confirmation
  - Create calendar events and send invitations
- Attachment understanding:
  - Summarize PDF and DOCX attachments
- AI usage:
  - OpenAI API **server-side only**
  - Structured outputs using strict JSON Schema
  - Persist `prompt_version`, `schema_version`, and `model_id` with results

---

## Fixed Technical Choices (Do Not Re-Decide)

### Frontend
- **Next.js (TypeScript)**
- App Router
- PWA-capable
- Located in `/web`

### Backend
- **Python 3.11**
- **FastAPI**
- Two ASGI apps:
  - Public API: `/backend/app/main_api.py`
  - Internal worker: `/backend/app/main_worker.py`
- Located in `/backend`

### Data
- **Postgres** (local via Docker Compose; prod via Cloud SQL)
- SQLAlchemy 2.x ORM
- Alembic migrations

### Infrastructure Targets (later phases)
- Google Cloud Run
- Cloud SQL
- Pub/Sub
- Cloud Tasks
- Cloud Scheduler
- Secret Manager
- KMS (for token encryption)

### Local Development
- `docker-compose` for Postgres
- API and worker run locally

---

## Hard Constraints (Must Always Be Followed)

- **Do NOT ask clarifying questions.** Make reasonable defaults and document them.
- **Do NOT leave TODOs.** If something is complex, implement a minimal working version and clearly document follow-ups.
- **Never include real secrets** in the repository.
  - Provide `.env.example` instead.
- **Never send emails automatically.**
  - Only create Gmail drafts.
- **“Delete” means TRASH**, not permanent delete, unless explicitly enabled.
- **Snooze is app-level**, implemented via labels + inbox removal + scheduled resurfacing.
- Code quality matters:
  - Clear structure
  - Docstrings and comments
  - Readable, boring, maintainable solutions
- AI safety and consistency:
  - All OpenAI calls go through a single backend wrapper
  - Enforce JSON Schema validation
  - Retry once on schema failure with repair prompt

---

## OpenAI Integration Rules

- All OpenAI API calls **must be server-side**.
- Never expose API keys to the browser.
- Implement the OpenAI client in:
  - `/backend/app/services/llm_client.py`
- Required behaviors:
  - Structured outputs with JSON Schema
  - Schema validation
  - One automatic repair retry on invalid output
  - Logging limited to hashes, token counts, and metadata — **never raw email bodies**

---

## Google Integration Rules

- Use official libraries:
  - `google-auth`
  - `google-api-python-client`
- OAuth:
  - Authorization Code flow
  - `access_type=offline`
  - `prompt=consent`
- Expect **weekly-ish reauthorization** in Testing mode.
  - Handle via in-app “Reconnect Google” UX.
  - Never require token pasting.
- Gmail push notifications:
  - Use Pub/Sub
  - Renew `watch` at least every 7 days (daily recommended)
- Gmail history:
  - Use `history.list`
  - Handle invalid history IDs with fallback full sync

---

## Output Expectations

Every task should result in:

1. **Working code** that runs locally.
2. **Clear README updates** describing how to run, test, or deploy changes.
3. **Formatted and linted code**.
4. **Tests** where they materially reduce risk (unit tests minimum; integration stubs acceptable).

When writing code:
- Prefer explicitness over cleverness.
- Prefer correctness over performance (optimize later).
- Prefer deterministic behavior over probabilistic magic.

---

## Completion Checklist (for Every Task)

Before finishing any task, you must:

1. Ensure the code builds and runs locally.
2. Run formatters and linters (or explain and fix failures).
3. Update README if behavior or setup changed.
4. Leave the repository in a clean, comprehensible state.

---

## Proceed

With these rules in effect, **proceed with the requested step** exactly as instructed.

Do not re-interpret these instructions unless explicitly told to update this file.
