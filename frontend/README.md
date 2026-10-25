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

`npm.cmd run build` type-checks the app and creates `dist/`. `npm.cmd run preview` serves a local preview with the same API proxy when the build has no API base URL configured. `npm.cmd run test:api` runs database-free API-client tests, also included at the start of `npm.cmd test`. The client tests compile the real module with local and production base URLs and stub fetch; they never contact Render. Browser tests always use the isolated local API, even if a production URL is set in your environment.

## Deploy to Vercel with the Render backend

After reviewing and publishing the code yourself, import `Kanishq-Potdar/car-dealership-inventory` into Vercel. No deployment is performed by these instructions or the build script.

| Vercel setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Node.js version | 24.x (matches the local test environment) |
| Production environment variable | `VITE_API_BASE_URL=https://car-dealership-inventory-hcpa.onrender.com` |

Set the variable in Vercel's **Production** environment before building. Its value is the backend origin, without `/api`; the client appends `/api` and the endpoint path. Trailing slashes are removed. For example, login goes to `https://car-dealership-inventory-hcpa.onrender.com/api/auth/login`. Authorization headers, JSON requests and error handling are unchanged.

Vite embeds `VITE_*` values in the public JavaScript bundle at build time. Changing the value requires another build/deployment. Never set `DATABASE_URL`, database passwords, `JWT_SECRET`, access tokens or private credentials as frontend variables. The URL is public configuration. See [Vite environment variables](https://vite.dev/guide/env-and-mode) and [Vercel's Vite documentation](https://vercel.com/docs/frameworks/frontend/vite).

For local development leave `VITE_API_BASE_URL` unset or empty, as shown in [.env.example](.env.example). Vite's existing `/api` proxy and optional `API_TARGET` continue working. `API_TARGET` only affects the local Vite server; it cannot configure a deployed static build. The application uses hash routes such as `/#/register`, so no SPA rewrite or Vercel API proxy is required for the current routes.

### Render CORS configuration

Once Vercel assigns the production URL, set **`CORS_ALLOWED_ORIGINS` on the Render backend** to a JSON array containing that exact origin, for example:

```text
["https://car-dealership-inventory-flame.vercel.app"]
```

Replace the example with the actual URL's scheme and host, without a path (e.g. `https://car-dealership-inventory-flame.vercel.app`). For a custom domain, add its exact origin to the array as well. Do not use `*` or a wildcard for all Vercel subdomains. Preview URLs are denied unless explicitly added; only enable a preview against this backend if you intend it to access the same data. A separate staging backend is preferable for preview testing.

Deploy the backend code containing the CORS middleware and restart/redeploy Render after setting the variable. Defaults allow no cross-origin browser access. The allowlist accepts JSON arrays only and invalid origin values fail startup. Only GET/POST/PUT/DELETE and Authorization/Content-Type are permitted for cross-origin API calls. Cookies are not enabled; JWT Bearer authentication and admin checks still apply. CORS controls browser access, not API authorization. See [FastAPI CORS documentation](https://fastapi.tiangolo.com/tutorial/cors/).

Preserve the existing Render database and signing-secret settings. For a service rooted at `backend`, the build command is `pip install -r requirements.txt` and the start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, with `/health` as its health-check path. If the existing service uses the repository root instead, its equivalent commands are `pip install -r backend/requirements.txt` and `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`; do not switch directories without also matching the commands. `DATABASE_URL` must retain the `postgresql+psycopg://` driver prefix, and `JWT_SECRET` stays on Render only. No schema migration, initialization or seeding is required for this change. See [Render's FastAPI deployment guide](https://render.com/docs/deploy-fastapi).

After both deployments, check `/health`, then use the Vercel UI and browser Network panel to confirm API requests target Render and responses have `Access-Control-Allow-Origin` matching the Vercel origin. Sign in with an existing account and verify catalogue access; avoid test purchases or registrations against production data. A successful local build does not verify the final deployed CORS configuration.

## API behavior and scope

- Registration uses full name, email and a 12–128 character password. Successful registration logs in automatically.
- JWTs stay in tab-scoped session storage (memory if storage is blocked). Expiration and API `401` responses return the user to sign-in. Passwords are never persisted. As with any JavaScript-accessible token, preventing XSS remains important.
- Main search uses the existing backend `q` parameter for partial matching and relevance ranking. Brand/model/category multi-selects use OR within each group and AND between groups; model options follow selected brands. Since the API has no multi-value, condition or sort parameters, these refinements apply locally to the returned results. Options and suggestions come from the full catalogue. Inclusive price bounds are sent to the backend. This approach assumes the current unpaginated catalogue API; server-side facets/pagination will be needed for much larger inventories.
- Customers see purchase actions only; admins see inventory management rows only. Role visibility is a UI choice, not an authorization boundary. Purchases consume one unit after confirmation. Zero-stock buttons are disabled; the backend remains responsible for atomic stock enforcement.
- Admins can create/edit/delete listings and edit prices. Condition is included; year is optional. Stock increases/decreases call the atomic `/adjust-stock` endpoint with a signed delta. Alerts come from `/alerts` and use its configured threshold; they are not guessed from local counts. Full listing and price edits require `PUT`. The UI reads fresh data before saving and preserves current quantity, but without a backend PATCH/version precondition a concurrent change between that read and PUT can still be overwritten. Stock adjustment actions do not have this limitation.
- Prices are shown without a currency symbol because the API does not define a currency. The vehicle art is a generic, labeled illustration; the API has no photo field.
- There is no payment processing or order history. Explicit stock controls use the existing adjustment API; the separate restock API remains available.
