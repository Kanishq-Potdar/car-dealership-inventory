# Car Dealership Inventory System

> **Deployment documentation:** The sections below describe the earlier authentication checkpoint and have not yet been fully refreshed. The repository now includes vehicle inventory and a React frontend. Use the [current frontend setup and Vercel/Render deployment guide](frontend/README.md#deploy-to-vercel-with-the-render-backend) and [backend operations guide](backend/README.md) for the current application. Deployment requires a public `VITE_API_BASE_URL` in Vercel and an exact `CORS_ALLOWED_ORIGINS` allowlist on Render.

A TDD-focused software engineering assignment for a car dealership inventory system. The current checkpoint implements the PostgreSQL connection and authentication foundation. **Vehicle inventory and the frontend are not implemented yet.**

## Current functionality

| Area | Status |
| --- | --- |
| FastAPI health endpoint | Implemented: `GET /health` returns `{"status":"ok"}`. This is application liveness, not a database health endpoint. |
| PostgreSQL connectivity | Implemented: SQLAlchemy connection check runs `SELECT 1`. |
| Registration | Implemented: users are persisted with Argon2id password hashes and the `customer` role. |
| Login | Implemented: email/password login returns an HS256-signed JWT valid for 30 minutes. |
| JWT verification | Implemented as the reusable `get_current_user` dependency; checks signature, expiration, required claims, and an existing user. |
| Role handling | Registration rejects client-supplied roles. The authentication dependency returns the current database user, rather than trusting a token's role. No admin workflow or role-restricted business endpoint exists yet. |
| Vehicle inventory API | Not implemented. |
| Frontend | Not implemented; there is no frontend directory, package manifest, or frontend run command. |
| Screenshots | Not supplied yet; see the screenshots section. |

Only `/health`, `/api/auth/register`, and `/api/auth/login` are application endpoints. FastAPI also provides API documentation. The `/protected` route used by tests belongs to a separate test application and is not a production endpoint.

## Tech stack

- Python 3.13 (current environment verified with Python 3.13.5).
- FastAPI and Uvicorn for the backend API.
- PostgreSQL 17, started with Docker Compose.
- SQLAlchemy and psycopg for database access.
- Pydantic and pydantic-settings for validation and environment configuration.
- pwdlib with Argon2 for password hashing, PyJWT for tokens, and email-validator for email validation.
- pytest and FastAPI TestClient/httpx for tests.

Exact Python dependency versions are in [backend/requirements.txt](backend/requirements.txt). No frontend framework is recorded as implemented in this repository.

## Project structure

```text
.
|-- README.md
|-- PROMPTS.md
|-- .env.example
|-- docker-compose.yml
`-- backend/
    |-- requirements.txt
    |-- app/
    |   |-- main.py          # FastAPI application, routes, validation errors
    |   |-- database.py      # Environment settings, connection pool, sessions
    |   |-- models.py        # SQLAlchemy user model
    |   |-- auth.py          # Registration, login, JWT authentication dependency
    |   `-- init_db.py       # Creates missing tables; does not migrate existing ones
    `-- tests/
        |-- test_health.py
        |-- test_database.py
        `-- test_auth.py
```

The local `.env` and `.venv/` are deliberately ignored by Git.

## Local setup

These instructions use **Windows PowerShell**, matching the current development environment. Install Python 3.13, Git, and Docker Desktop with Docker Compose, and start Docker Desktop before starting PostgreSQL. The backend runs on the host; only PostgreSQL runs in Docker.

### 1. Get the project and install backend dependencies

For a new checkout:

```powershell
git clone https://github.com/Kanishq-Potdar/car-dealership-inventory.git
cd car-dealership-inventory
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

For an existing checkout, use its project directory and existing `.venv` instead of creating another checkout or virtual environment. Explicit virtual-environment paths below mean activation is not required.

### 2. Configure environment variables

From the project root, copy the template only if `.env` does not already exist:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Edit your local `.env` using [.env.example](.env.example) as the template:

| Variable | Purpose |
| --- | --- |
| `DB_PASSWORD` | Password used by Docker Compose when PostgreSQL first initializes. Replace `replace-me`. |
| `DATABASE_URL` | SQLAlchemy connection URL using the `postgresql+psycopg` driver. Use the same password as `DB_PASSWORD`. |
| `JWT_SECRET` | A randomly generated signing secret of at least 32 characters. There is no application fallback secret. |

For the supplied Compose configuration, the database user and database name are both `dealership`, with host `localhost` and port `5432` when the backend runs on the host. The URL shape is:

```text
postgresql+psycopg://dealership:<URL-encoded password>@localhost:5432/dealership
```

The angle-bracket text is an explanation, not a literal password. URL-encode reserved characters in the password when placing it in `DATABASE_URL`; `DB_PASSWORD` remains the actual password. Keep `.env` private and out of screenshots or chat logs. Process environment variables override `.env` values.

To generate a signing secret without printing it, run this from the root after copying `.env`. It preserves an existing nonempty secret:

```powershell
@'
from pathlib import Path
import secrets
from dotenv import dotenv_values, set_key

path = Path('.env')
assert path.exists(), 'Copy .env.example to .env first'
if not dotenv_values(path).get('JWT_SECRET'):
    set_key(path, 'JWT_SECRET', secrets.token_hex(32))
print('JWT_SECRET configured; value not displayed.')
'@ | .\.venv\Scripts\python.exe -B -
```

### 3. Start PostgreSQL

From the project root:

```powershell
docker compose up -d db
docker compose ps
```

Wait for the database service to become healthy. The container is named `dealership-db`; data persists in the Compose-managed `postgres_data` volume.

To stop the service while preserving its data:

```powershell
docker compose stop db
```

Changing `DB_PASSWORD` in `.env` does not change a password in an already initialized database volume. If credentials disagree, reconcile the existing database credentials and configuration; do not delete the volume to make tests pass.

### 4. Initialize and run the backend

From the project root:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.init_db
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`app.init_db` creates missing tables. It does not drop data, seed an admin, or upgrade an existing table's structure. Restart the backend after changing environment configuration.

Open:

- API documentation: <http://127.0.0.1:8000/docs>
- Health endpoint: <http://127.0.0.1:8000/health>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

The interactive API documentation is a development tool, not the planned dealership frontend.

### 5. Frontend setup

There is no frontend to install or start at this checkpoint. Do not run assumed `npm install` or `npm run dev` commands. Add the actual framework, prerequisites, environment settings, install/build/run commands, and frontend tests here when that implementation exists.

## Authentication API

Both endpoints accept JSON. Example values below are disposable demonstration data, not real credentials. Calling registration against the normal running backend creates a development user.

### Register: `POST /api/auth/register`

```json
{
  "full_name": "Alex Customer",
  "email": "alex@example.com",
  "password": "A long password 123!"
}
```

Required fields are `full_name`, `email`, and `password`. Names are trimmed and must be 1-100 characters. Email addresses are validated, trimmed, and normalized to lowercase. Registration passwords must be 12-128 characters. Extra fields, including `role`, are rejected.

- `201`: returns `id`, `full_name`, `email`, and `role` (`customer`).
- `409`: email already registered, including normalized case variants.
- `422`: missing/invalid fields or a supplied role.

Passwords are hashed before storage; password hashes are not returned. A database unique constraint protects email uniqueness, and failed inserts are rolled back.

### Login: `POST /api/auth/login`

```json
{
  "email": "alex@example.com",
  "password": "A long password 123!"
}
```

- `200`: returns `access_token` and `token_type` (`bearer`).
- `401`: `Invalid email or password`, with the same message for an unknown email and an incorrect password.
- `422`: invalid or missing request fields.

Tokens contain a subject (`sub`), issue time (`iat`), expiration (`exp`), and role. They are signed, not encrypted; they do not contain passwords. `get_current_user` accepts `Authorization: Bearer <token>`, permits HS256 only, requires `sub`, `iat`, and `exp`, validates time claims, and looks up the user in PostgreSQL. Invalid tokens or missing users return `401` with `WWW-Authenticate: Bearer`. This dependency is ready for future protected endpoints; no vehicle endpoint exists yet.

## Running tests

Start PostgreSQL and configure `.env` first. The tests use a real PostgreSQL connection and fail if it is unavailable; they do not silently skip database checks. A running Uvicorn process is not required.

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Focused suites:

```powershell
..\.venv\Scripts\python.exe -B -m pytest tests/test_health.py tests/test_database.py -q -p no:cacheprovider
..\.venv\Scripts\python.exe -B -m pytest tests/test_auth.py -q -p no:cacheprovider
```

Authentication tests create a unique schema inside an outer transaction on the configured PostgreSQL database. Dependency overrides direct ORM operations to that schema, and per-request sessions use savepoints. Teardown rolls back the transaction, including the schema. These are isolated schemas, **not a separate test database**. The configured database user needs permission to create schemas. Tests do not call `init_db` on development tables or reset development data. Future code that opens independent connections or bypasses the overridden session must preserve this isolation explicitly.

Coverage includes health, connectivity, registration persistence and hashing, duplicate emails, invalid input, role-assignment rejection, invalid credentials, signed tokens, and HTTP-level dependency acceptance/rejection for valid, expired, malformed, unsigned, incorrectly signed, wrong-algorithm, and missing-claim tokens.

Latest observed full-suite result during documentation review on **2026-10-25** (Python 3.13.5, existing Windows development environment):

```text
40 passed, 1 warning in 23.08s
```

The warning is the existing Starlette/httpx TestClient deprecation. It was not suppressed or fixed as part of documentation work. This result is not a claim that a fresh installation or another operating system was tested. The `-B` and `no:cacheprovider` options avoid writing Python bytecode and pytest caches during these runs.

## Screenshots

No screenshots have been supplied or embedded yet. Add genuine captures with captions when available:

- Current backend: API docs, registration/login responses, and the test result. Hide passwords, tokens, and private configuration.
- Future frontend: registration/login screens and inventory workflows, only after those features are implemented.

No UI mockup or placeholder image is presented as a working application screenshot.

## AI usage and assignment evidence

See [PROMPTS.md](PROMPTS.md) for actual excerpts available from the development conversation, observed TDD output excerpts, a separately labeled activity summary, and the personal reflection still required from the student.

The original assignment brief was uploaded in a separate ChatGPT conversation and is not available in this repository. These documents cover the requirements established in the current conversation; they are **not a verified checklist against the complete original rubric**. The brief and any separate project plan are still needed for that final check.

## Remaining work

- Implement vehicle inventory and the frontend against the original assignment requirements.
- Document the real frontend setup and tests once it exists.
- Add genuine screenshots.
- Supply the original assignment brief/project plan, any required full AI transcripts or accessible chat links, and the student's own AI-usage reflection.
- Recheck documentation against the full rubric before submission. The current initializer is not a database migration system; future schema changes will need an explicit migration approach.
