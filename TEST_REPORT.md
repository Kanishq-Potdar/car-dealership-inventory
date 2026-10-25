# Test Report â€” Car Dealership Inventory System

## Legend

- **Rerun (this task):** test was actually run during the 2026-10-25 documentation session and output was observed directly.
- **Historical:** result was observed in an earlier development session and recorded in conversation evidence (verbatim pytest output). Not rerun during this task.
- **Not run:** test suite exists but was not executed (database unavailable or browser driver not installed during this task). No pass/fail claim is made.

---

## 1. Backend tests â€” database-free suites (Rerun: 2026-10-25)

**Command:**
```powershell
# From backend/, using .venv
..\\.venv\Scripts\python.exe -B -m pytest tests/test_cors.py tests/test_health.py tests/test_vehicle_search.py -v --tb=short -p no:cacheprovider
```

**Environment:** Python 3.13.5, pytest 9.1.1, Windows 11 (local development machine). PostgreSQL **not** required for these suites.

**Result:**
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\kanis\OneDrive\Desktop\Projects\AI Kata Car Dealership\backend
plugins: anyio-4.15.1
collected 53 items

tests/test_cors.py::test_main_installs_cors PASSED                       [  1%]
tests/test_cors.py::test_allowed_preflight[GET] PASSED                   [  3%]
tests/test_cors.py::test_allowed_preflight[POST] PASSED                  [  5%]
tests/test_cors.py::test_allowed_preflight[PUT] PASSED                   [  7%]
tests/test_cors.py::test_allowed_preflight[DELETE] PASSED                [  9%]
tests/test_cors.py::test_other_origins_rejected[https://other.vercel.app] PASSED [ 11%]
tests/test_cors.py::test_other_origins_rejected[https://motorhaus-test.vercel.app.evil.example] PASSED [ 13%]
tests/test_cors.py::test_other_origins_rejected[null] PASSED             [ 15%]
tests/test_cors.py::test_default_denies_cross_origin_and_local_health_works PASSED [ 16%]
tests/test_cors.py::test_cors_does_not_bypass_authentication PASSED      [ 18%]
tests/test_cors.py::test_unapproved_method_or_headers[PATCH-authorization] PASSED [ 20%]
tests/test_cors.py::test_unapproved_method_or_headers[POST-x-unapproved] PASSED [ 22%]
tests/test_cors.py::test_invalid_configuration_rejected[*] PASSED        [ 24%]
tests/test_cors.py::test_invalid_configuration_rejected[https://*.vercel.app] PASSED [ 26%]
tests/test_cors.py::test_invalid_configuration_rejected[null] PASSED     [ 28%]
tests/test_cors.py::test_invalid_configuration_rejected[ftp://example.com] PASSED [ 30%]
tests/test_cors.py::test_invalid_configuration_rejected[https://example.com/path] PASSED [ 32%]
tests/test_cors.py::test_invalid_configuration_rejected[https://user:pass@example.com] PASSED [ 33%]
tests/test_cors.py::test_invalid_configuration_rejected[https://example.com?x=1] PASSED [ 35%]
tests/test_cors.py::test_invalid_configuration_rejected[https://example.com#hash] PASSED [ 37%]
tests/test_cors.py::test_invalid_configuration_rejected[https://example.com:invalid] PASSED [ 39%]
tests/test_cors.py::test_multiple_explicit_origins_and_trailing_slash PASSED [ 41%]
tests/test_cors.py::test_cors_headers_present_on_unexpected_server_exception PASSED [ 43%]
tests/test_cors.py::test_cors_headers_absent_on_unexpected_exception_disallowed_origin PASSED [ 45%]
tests/test_health.py::test_health_endpoint_returns_ok PASSED             [ 47%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params0-indices0] PASSED [ 49%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params1-indices1] PASSED [ 50%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params2-indices2] PASSED [ 52%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params3-indices3] PASSED [ 54%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params4-indices4] PASSED [ 56%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params5-indices5] PASSED [ 58%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params6-indices6] PASSED [ 60%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params7-indices7] PASSED [ 62%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params8-indices8] PASSED [ 64%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params9-indices9] PASSED [ 66%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params10-indices10] PASSED [ 67%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params11-indices11] PASSED [ 69%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params12-indices12] PASSED [ 71%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params13-indices13] PASSED [ 73%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params14-indices14] PASSED [ 75%]
tests/test_vehicle_search.py::test_search_filters_and_sort[params15-indices15] PASSED [ 77%]
tests/test_vehicle_search.py::test_invalid_search_filters[params0] PASSED [ 79%]
tests/test_vehicle_search.py::test_invalid_search_filters[params1] PASSED [ 81%]
tests/test_vehicle_search.py::test_invalid_search_filters[params2] PASSED [ 83%]
tests/test_vehicle_search.py::test_invalid_search_filters[params3] PASSED [ 84%]
tests/test_vehicle_search.py::test_invalid_search_filters[params4] PASSED [ 86%]
tests/test_vehicle_search.py::test_invalid_search_filters[params5] PASSED [ 88%]
tests/test_vehicle_search.py::test_invalid_search_filters[params6] PASSED [ 90%]
tests/test_vehicle_search.py::test_invalid_search_filters[params7] PASSED [ 92%]
tests/test_vehicle_search.py::test_invalid_search_filters[params8] PASSED [ 94%]
tests/test_vehicle_search.py::test_invalid_search_filters[params9] PASSED [ 96%]
tests/test_vehicle_search.py::test_invalid_search_filters[params10] PASSED [ 98%]
tests/test_vehicle_search.py::test_search_still_requires_authentication PASSED [100%]

============================== warnings summary ===============================
..\\.venv\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is
  deprecated; install `httpx2` instead.

======================== 53 passed, 1 warning in 3.96s ========================
```

**Suites covered:** `test_cors.py` (24 tests), `test_health.py` (1 test), `test_vehicle_search.py` (28 tests).

**Warning note:** The `StarletteDeprecationWarning` about `httpx` vs `httpx2` is a pre-existing issue from the installed library version. It does not affect test outcomes and was not suppressed during this run.

**New tests included in this run:** `test_cors_headers_present_on_unexpected_server_exception` and `test_cors_headers_absent_on_unexpected_exception_disallowed_origin` (added in the CORS fix session, 2026-10-25). Both passed.

---

## 2. Backend tests â€” PostgreSQL-dependent suites (Historical)

These suites require a running PostgreSQL instance with `DATABASE_URL` and `JWT_SECRET` configured. They were **not rerun during this documentation task** because the database was not started. Results below are from conversation evidence.

### Full backend suite â€” prior to CORS additions

**Command used in development:**
```powershell
..\\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

**Observed result (historical, recorded in README during prior documentation task):**
```
40 passed, 1 warning in 23.08s
```

*This was 40 tests before `test_cors.py`, `test_vehicle_search.py`, `test_phase1.py`, and the Phase 1 suites were added.*

### JWT dependency stage â€” historical excerpt

Observed full-suite output, verbatim from Codex conversation (see PROMPTS.md Â§3):
```
40 passed, 1 warning in 8.40s
```

### Suites present that require PostgreSQL

| Test file | What it covers |
| --- | --- |
| `test_database.py` | PostgreSQL connectivity (`SELECT 1`) |
| `test_auth.py` | Registration, login, JWT HTTP acceptance/rejection |
| `test_inventory.py` | Vehicle CRUD, purchase, restock, stock constraints |
| `test_vehicles.py` | Vehicle API routes and authorization |
| `test_phase1.py` | Migration DDL, backfill, admin bootstrap, alerts, concurrent seed/stock |

**To run:** Start PostgreSQL with Docker Compose, configure `.env`, then from `backend/`:
```powershell
..\\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

---

## 3. Frontend API client tests (Rerun: 2026-10-25)

**Command:**
```powershell
# From frontend/
npm.cmd run test:api
```

**What it does:** Compiles `src/api.ts` with Vite's build-time env replacement and stubs `fetch`. Tests run entirely in Node.js â€” no database, no Render backend, no browser required.

**Result:**
```
npm notice run dealership-frontend@0.1.0 test:api
npm notice run node --test tests/api.test.mjs

âœ” API URL and request behavior with base "" (227.3022ms)
âœ” API URL and request behavior with base "https://car-dealership-inventory-hcpa.onrender.com" (45.8699ms)
âœ” API URL and request behavior with base " https://car-dealership-inventory-hcpa.onrender.com/ " (50.4778ms)
âœ” network and cancellation error behavior is preserved (23.6884ms)
â„¹ tests 4
â„¹ suites 0
â„¹ pass 4
â„¹ fail 0
â„¹ cancelled 0
â„¹ skipped 0
â„¹ todo 0
â„¹ duration_ms 2447.6994
```

**Coverage:** URL construction with empty base (local proxy), production base URL, and whitespace/trailing-slash variants; authorization header; Content-Type injection; 204/401/422/502 error handling; network failure; AbortError propagation.

---

## 4. TypeScript type check (Rerun: 2026-10-25)

**Command:**
```powershell
# From frontend/
npm.cmd run check
```

**Result:** Exit code 0, no type errors, no output (clean).

---

## 5. Frontend browser integration tests (Not run during this task)

**Command:**
```powershell
# From frontend/
npx.cmd playwright install chromium
npm.cmd test
```

**Why not run:** Requires PostgreSQL running and `backend/` dependencies installed; database was not started during this documentation task.

**What is covered** (from `frontend/README.md`): real registration/login, duplicate registration, role-specific actions and backend authorization, multi-select/condition/price filters, `q` search and suggestions, sorting, admin CRUD/price editing/stock adjustments/alerts, purchasing, zero-stock controls, session persistence/logout, mobile layout. Server-error/loading/401 UI cases use explicitly mocked responses.

**Evidence of prior run:** Three Playwright-generated screenshots exist in `frontend/test-results/` (gitignored, present locally, timestamped 2026-10-25 15:10 IST):
- `storefront-desktop.png` (101 KB) â€” customer storefront, desktop layout
- `storefront-mobile.png` (106 KB) â€” customer storefront, mobile layout
- `admin-inventory.png` (101 KB) â€” admin workspace with inventory table and stock-watch panel

These are test fixtures from an isolated temporary schema, not production data. They have been copied to `docs/screenshots/` to be tracked in the repository.

---

## 6. Production build check (Not run during this task)

**Command:**
```powershell
# From frontend/
npm.cmd run build
```

**What it does:** Runs `tsc --noEmit` (type-check) then `vite build`, outputting to `frontend/dist/`. This is the artifact Vercel deploys.

**Not run during this task.** The TypeScript check (Â§4) passed, which covers the type-check step. The Vite bundling step was not separately verified in this session.

---

## 7. Summary table

| Suite | Status | Tests | Date |
| --- | --- | --- | --- |
| Backend: CORS (`test_cors.py`) | âœ… Rerun â€” 24/24 passed | 24 | 2026-10-25 |
| Backend: health (`test_health.py`) | âœ… Rerun â€” 1/1 passed | 1 | 2026-10-25 |
| Backend: search logic (`test_vehicle_search.py`) | âœ… Rerun â€” 28/28 passed | 28 | 2026-10-25 |
| Backend: connectivity (`test_database.py`) | â¬œ Not rerun (needs PostgreSQL) | â€” | Historical: 40 passed |
| Backend: auth (`test_auth.py`) | â¬œ Not rerun (needs PostgreSQL) | â€” | Historical: 40 passed |
| Backend: inventory (`test_inventory.py`, `test_vehicles.py`) | â¬œ Not rerun (needs PostgreSQL) | â€” | Historical: full suite passed |
| Backend: Phase 1 (`test_phase1.py`) | â¬œ Not rerun (needs PostgreSQL) | â€” | Historical: present |
| Frontend: API client (`tests/api.test.mjs`) | âœ… Rerun â€” 4/4 passed | 4 | 2026-10-25 |
| Frontend: TypeScript check | âœ… Rerun â€” clean | â€” | 2026-10-25 |
| Frontend: browser E2E (Playwright) | â¬œ Not rerun (needs PostgreSQL + browser) | â€” | Screenshots from 2026-10-25 15:10 |
| Frontend: production build (`vite build`) | â¬œ Not run this task | â€” | â€” |

---

## 8. Open items

- Run the full backend suite (including `test_database.py`, `test_auth.py`, `test_inventory.py`, `test_vehicles.py`, `test_phase1.py`) against a live PostgreSQL instance to confirm the current 53-test database-free baseline extends cleanly.
- Screenshots: genuine Playwright captures are now tracked in `docs/screenshots/`. To update or regenerate them, run `npm test` from `frontend/` with PostgreSQL running.
- Run `npm run build` to verify the production bundle builds without errors.
- Verify the deployed Render backend responds at `/health` and that the Vercel frontend (`https://car-dealership-inventory-flame.vercel.app`) receives the correct `Access-Control-Allow-Origin` header from the Render origin.
