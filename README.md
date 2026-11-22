# OOP-AI

AI-powered Object-Oriented Concepts examination and learning mobile application.

LEARN • PRACTICE • EXCEL

## Repository layout

| Path | What it is |
| --- | --- |
| `backend/` | FastAPI + SQLAlchemy + Alembic API (Python 3.10+) |
| `mobile/` | Expo / React Native / TypeScript app using Expo Router |
| `docker-compose.yml` | Local PostgreSQL 16 |

## Status

Milestone 1 (foundation + authentication) is implemented:

- Register, sign in with email or student ID, sign out, refresh, `me`, forgot/reset password.
- Argon2 password hashing, short-lived JWT access tokens, rotating hashed refresh tokens with reuse detection,
  revocation on logout, single-use expiring reset tokens, rate limiting on auth routes.
- Mobile sign-in, sign-up, forgot-password and reset-password screens using the Coffee & Paper design tokens
  (`mobile/src/theme/tokens.ts`) and reusable components (`mobile/src/components/`).
- The signed-in home screen is a placeholder until the dashboard design is provided.

Milestone 2 (backend only so far) adds the OOC topic library:

- `topic_categories` → `topic_groups` (chapters) → `topics`, plus `topic_prerequisites`, with stable slugs,
  ordering and active flags. The 12-category, 179-topic syllabus is seeded with `python -m app.seed` (idempotent;
  existing rows and admin edits are never overwritten).
- Student API (signed in): `GET /api/topics` (active tree), `GET /api/topics/categories`,
  `GET /api/topics/search?q=`, `GET /api/topics/{id}`, `POST /api/topics/selection` (expands selected
  categories/chapters/topics into a de-duplicated topic list with per-category counts).
- Admin API (`/api/admin/topics/...`): full tree incl. inactive, create/edit/move/deactivate categories, chapters
  and topics, reorder, set prerequisites (self and circular dependencies rejected), and re-seed.
- The topic-selection screen is not built yet; it waits for the design reference.

Exams, AI generation/evaluation, code execution and analytics are later milestones.

## Prerequisites

- Python 3.10+
- Node.js 20+ (22 LTS recommended)
- Docker (for PostgreSQL), or a local PostgreSQL 16

## Backend

```bash
docker compose up -d db

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Set JWT_SECRET_KEY in .env:
python -c "import secrets; print(secrets.token_urlsafe(64))"

alembic upgrade head
python -m app.seed          # load the OOC topic library
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

In development without SMTP settings, password reset emails (link + reset code) are printed to the server console.

### Backend tests and lint

```bash
cd backend
pytest                      # uses SQLite by default
TEST_DATABASE_URL=postgresql+psycopg://oopai:oopai@localhost:5432/oopai_test pytest   # against PostgreSQL
ruff check . && ruff format --check .
```

### Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Mobile

```bash
cd mobile
npm install
cp .env.example .env        # EXPO_PUBLIC_API_URL, use your LAN IP on a physical device
npx expo start              # press w for web, or scan the QR code with a development build / Expo Go
```

Checks:

```bash
npm run typecheck
npm run lint
npx expo-doctor
```

## Security notes

- Secrets (JWT key, SMTP, future AI keys) live only in `backend/.env`; never in the mobile app.
- `EXPO_PUBLIC_*` variables are bundled into the app and must not contain secrets.
- Refresh tokens are stored in Expo SecureStore on native (localStorage on web).
