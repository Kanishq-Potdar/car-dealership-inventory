# Motorhaus backend — Phase 1 operations

Run the following commands from `backend/` using the existing root virtual environment. PostgreSQL must be running and the root `.env` must contain `DATABASE_URL` and `JWT_SECRET`. No additional Python packages are required.

## Schema initialization and migration

For a fresh database, create missing tables first:

```powershell
..\.venv\Scripts\python.exe -B -m app.init_db
```

For **both existing and fresh databases**, apply the explicit Phase 1 migration:

```powershell
..\.venv\Scripts\python.exe -B -m app.migrate
```

`init_db` still uses `create_all`; it does **not** upgrade an existing table. `app.migrate` runs explicit PostgreSQL DDL in one transaction. It adds `condition`, its check/not-null/default constraints, an internal unique nullable `sample_key`, and indexes for quantity, price, and lowercase category. Existing rows without condition are backfilled as **used**. This is a conservative compatibility default, not a claim that their condition was verified; review those listings before publishing them. Existing non-null conditions, IDs, prices, stock, users and other vehicle details are preserved. Invalid pre-existing condition values cause a rollback rather than being silently replaced.

The migration is repeatable and serializes competing migration commands with an advisory transaction lock. It does not drop/reset tables or seed accounts/data. It uses a five-second lock timeout and a sixty-second statement timeout; on contention or timeout the transaction rolls back. Run it during a quiet window, especially on larger catalogues, because ordinary DDL and index creation can block writes. Back up valuable data before schema changes. There is no destructive downgrade command.

Optional typo tolerance:

```powershell
..\.venv\Scripts\python.exe -B -m app.migrate --enable-trigram
```

The inspected PostgreSQL 17 installation offers `pg_trgm` 1.6 but did not initially have it installed. The optional flag tries to install it, and creates GIN indexes on lowercase make, model and combined make/model when it is installed. A failed installation is rolled back to a savepoint and reported; the core migration can still complete. Without the extension, normal partial search remains available. No extension is installed automatically by an API request. If an administrator installs it separately, rerun migration to add its indexes. Small tables may correctly use sequential scans instead of indexes. See the [PostgreSQL trigram documentation](https://www.postgresql.org/docs/17/pgtrgm.html).

## Optional sample catalogue

```powershell
..\.venv\Scripts\python.exe -B -m app.seed_catalogue
```

This explicitly inserts the [60-row SAMPLE catalogue](data/README.md), with illustrative INR prices, conditions, years and quantities. It is not real dealership stock or a live price feed. Seeding is not part of initialization/migration. Stable sample keys and PostgreSQL `ON CONFLICT DO NOTHING` prevent duplicates even when seed commands run concurrently. Existing rows, including edited sample rows, are never overwritten. A deleted sample is inserted again on a later seed run. User-created listings are independent even when their make/model resembles a sample. The API does not accept a client-supplied `sample_key`.

## First administrator

After initialization/migration, run this in an interactive terminal:

```powershell
..\.venv\Scripts\python.exe -B -m app.bootstrap_admin
```

Enter full name, email, password and password confirmation when prompted. Password prompts are hidden; if secure input is unavailable the command refuses to continue. Do not pass passwords in command arguments or paste them into documentation. Validation and Argon2 hashing reuse the existing registration implementation. No plaintext password is stored or printed.

The command refuses to run if **any admin already exists**, or if the normalized email belongs to any account. It never promotes, replaces or resets an existing customer. Concurrent bootstrap commands are serialized with a database table lock; ordinary registrations cannot race the duplicate check. Lock contention fails safely. This command provisions only the first admin; further admin management/password recovery is outside this phase. Public registration continues to reject supplied roles and create customers only.

## API additions and compatibility

- Every listing now returns `condition`, either `new` or `used`. Explicit null/invalid values return `422`. Legacy create requests that omit condition receive `used`. Full-replacement `PUT` retains an existing condition when the caller omits that field, so the unchanged frontend cannot accidentally reset it. Year remains optional.
- `GET /api/vehicles/search` retains `make`, `model`, `category`, `min_price` and `max_price`; make/model now use case-insensitive **partial** matching. Category stays a case-insensitive exact filter and price bounds remain inclusive. The optional `q` searches make, model and their combined name. Multiple filters are combined with AND. Search ranks exact matches before prefixes, substrings, then trigram-only matches; ID breaks ties. SQL wildcard characters in user input are literal. Installed trigram support uses a transaction-local similarity threshold of 0.3 for queries of at least three characters. Without it, spelling errors are not corrected.
- `POST /api/vehicles/{id}/adjust-stock` accepts `{"delta": -2}` or `{"delta": 5}` and is admin-only. Delta must be a nonzero integer within PostgreSQL's signed positive/negative integer range. A conditional atomic update rejects a negative result or overflow with `409`, rejects invalid input with `422`, and returns `404` for a missing vehicle. Successful responses contain the updated listing. The existing atomic purchase/restock operations are preserved.
- `GET /api/vehicles/alerts` is admin-only and returns `{"threshold": 3, "vehicles": [...]}`. It includes stock at or below the configured threshold, including zero, ordered by quantity then ID. Add `?out_of_stock=true` to return only zero-stock listings.
- Set `LOW_STOCK_THRESHOLD=3` in the root `.env` or process environment to configure alerts; the valid range is 0–2147483647. Restart the backend after configuration changes. Invalid configuration is rejected rather than silently clamped.

Admin authorization uses the **current database role**, not a trusted client-supplied role or a stale JWT role claim. Unauthorized callers receive the existing `401`/`403` behavior. No frontend changes are included; its older exact-search help text and missing condition/alerts/adjustment controls can be updated in a later frontend phase.

## Tests

```powershell
..\.venv\Scripts\python.exe -B -m pytest tests/test_phase1.py -q -p no:cacheprovider
..\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Tests use unique temporary schemas, not development tables. Migration/backfill and optional extension installation are tested inside rollback-only transactions. The trigram test requires the available extension and permission to create it; it fails clearly rather than claiming typo tolerance was tested when it was not. Concurrent seed/bootstrap/stock tests use committed temporary schemas with independent connections, dropping only the schema each fixture created during cleanup. Normal completion removes test data; forcibly terminating a process may leave an isolated test schema behind.
