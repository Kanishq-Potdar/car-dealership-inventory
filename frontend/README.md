# Motorhaus frontend

React, TypeScript, Vite and Tailwind CSS frontend for the existing dealership API. No frontend framework, router, component library or HTTP client beyond React and the browser's fetch API is required. Playwright is a development dependency for browser integration tests.

## Run locally (Windows PowerShell)

Start PostgreSQL with the root Compose configuration and configure the root `.env` as described in the root README. Initialize missing tables and run FastAPI from `backend/`:

```powershell
..\.venv\Scripts\python.exe -B -m app.init_db
..\.venv\Scripts\python.exe -B -m app.migrate
..\.venv\Scripts\python.exe -B -m uvicorn app.main:app --reload
```

In a second terminal, from `frontend/` (Node.js 24 was used):

```powershell
npm.cmd ci
npm.cmd run dev
```

Open the local URL printed by Vite, normally `http://127.0.0.1:5173`. Vite forwards `/api` to `http://127.0.0.1:8000`, so no backend CORS change is needed. To use a different backend, set `$env:API_TARGET = 'http://127.0.0.1:8001'` before starting Vite. Never put database credentials or the JWT signing secret in frontend configuration.

Registering creates a customer. Use an existing, deliberately provisioned admin account to access add/edit/delete controls. This app does not grant admin privileges or seed a development admin. The role claim controls UI visibility only; the backend checks the current database role. If a role changes, sign in again to refresh the UI.

## Checks

```powershell
npm.cmd run check
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd test
```

The browser tests require the project's root `.venv`, installed backend dependencies and running PostgreSQL. They start dedicated API/Vite servers on ports 8011/5174; those ports must be free. The runner creates a random `test_frontend_<uuid>` schema, seeds test-only fixtures, and drops only that schema in `finally`. No development table is reset or seeded. If the runner is forcibly killed, its disposable schema may remain. Tests fail rather than silently skipping an unavailable database. Run the Python backend tests separately from `backend/` as before.

Tests cover real registration/login, duplicate registration, role-specific actions and backend authorization, multi-select/condition/price filters, q search and suggestions, sorting, admin CRUD/price editing/stock adjustments/alerts, purchasing, zero-stock controls, session persistence/logout and mobile layout. Server-error/loading/401 UI cases use explicitly mocked responses. Screenshots from the isolated test inventory are written to ignored `test-results/`; they are test fixtures, not real dealership listings.

`npm.cmd run build` type-checks the app and creates `dist/`. `npm.cmd run preview` serves a local preview with the same API proxy. For deployment, serve `dist/` over HTTPS and configure the hosting reverse proxy to forward `/api` to FastAPI; Vite's development proxy is not part of the static build.

## API behavior and scope

- Registration uses full name, email and a 12–128 character password. Successful registration logs in automatically.
- JWTs stay in tab-scoped session storage (memory if storage is blocked). Expiration and API `401` responses return the user to sign-in. Passwords are never persisted. As with any JavaScript-accessible token, preventing XSS remains important.
- Main search uses the existing backend `q` parameter for partial matching and relevance ranking. Brand/model/category multi-selects use OR within each group and AND between groups; model options follow selected brands. Since the API has no multi-value, condition or sort parameters, these refinements apply locally to the returned results. Options and suggestions come from the full catalogue. Inclusive price bounds are sent to the backend. This approach assumes the current unpaginated catalogue API; server-side facets/pagination will be needed for much larger inventories.
- Customers see purchase actions only; admins see inventory management rows only. Role visibility is a UI choice, not an authorization boundary. Purchases consume one unit after confirmation. Zero-stock buttons are disabled; the backend remains responsible for atomic stock enforcement.
- Admins can create/edit/delete listings and edit prices. Condition is included; year is optional. Stock increases/decreases call the atomic `/adjust-stock` endpoint with a signed delta. Alerts come from `/alerts` and use its configured threshold; they are not guessed from local counts. Full listing and price edits require `PUT`. The UI reads fresh data before saving and preserves current quantity, but without a backend PATCH/version precondition a concurrent change between that read and PUT can still be overwritten. Stock adjustment actions do not have this limitation.
- Prices are shown without a currency symbol because the API does not define a currency. The vehicle art is a generic, labeled illustration; the API has no photo field.
- There is no payment processing or order history. Explicit stock controls use the existing adjustment API; the separate restock API remains available.
