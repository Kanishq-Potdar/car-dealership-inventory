# AI usage record

## Scope and evidence status

This project used three AI tools across its development:

- **ChatGPT** (OpenAI) — used by the student for assignment planning and initial brainstorming in a separate conversation. A shared conversation link was supplied by the student: https://chatgpt.com/share/6addf90d-1d20-83ec-98a2-763aa1f8af27 (labeled as a shared conversation link, not a raw transcript; public accessibility has not been independently verified).
- **OpenAI Codex** — used for AI-assisted implementation, testing, review, Git operations, and documentation drafting throughout the development conversation. Codex co-authorship is recorded in every commit from `ec26313` onward.
- **Antigravity** (Google DeepMind) — used in the final CORS fix session (`2b52df2`) and documentation update. Antigravity co-authorship is recorded in that commit.

The evidence below comes from messages and tool outputs visible in the Codex and Antigravity development conversations, alongside the student-provided ChatGPT link. It is **a partial record, not a complete chat export**.

The original assignment attachment is not stored in this repository. For the ChatGPT brainstorming session, the student has supplied a shared conversation link (`https://chatgpt.com/share/6addf90d-1d20-83ec-98a2-763aa1f8af27`), labeled as a shared conversation link rather than a raw transcript (public accessibility has not been independently verified). No offline raw transcript for ChatGPT is stored in the repository. For OpenAI Codex and Antigravity, no shared chat URLs or full transcript exports have been supplied beyond the excerpts and summaries below. This file does not invent links, conversations, message timestamps, or a personal reflection. Dates refer to this record's preparation (2026-10-24 / 2026-10-25); they are not asserted to be the timestamp of every quoted message.

Only blocks explicitly labeled **verbatim excerpt** or **complete verbatim user message** reproduce chat text. Excerpts can omit surrounding messages and tool output; each quoted block is contiguous. Other sections are editorial summaries, not raw logs.

---

## Evidence index

| Tool | Evidence type | Status |
| --- | --- | --- |
| ChatGPT (assignment brainstorming) | Shared conversation link | Supplied: https://chatgpt.com/share/6addf90d-1d20-83ec-98a2-763aa1f8af27 (shared link, not raw transcript; public accessibility unverified) |
| OpenAI Codex (database layer) | Verbatim user message + assistant excerpts + pytest output | ✓ Available below (§1) |
| OpenAI Codex (authentication) | Verbatim user message + assistant excerpts + pytest output | ✓ Available below (§2) |
| OpenAI Codex (JWT dependency) | Complete verbatim user message + assistant excerpt + pytest output | ✓ Available below (§3) |
| OpenAI Codex (vehicle inventory, search, frontend, migration, seeding, admin) | Activity summary | ✓ Summary below (§5); raw log **PENDING** |
| Antigravity (CORS fix and 500 header test) | Activity summary from tool session | ✓ Summary below (§6); transcript stored in local `.gemini/` but not exported |
| Student personal reflection | Written by student | **PENDING** — see §7 |

---

## Assignment requirements known from this conversation

- Provide a root README with overview, stack, setup, tests, current features, and screenshots.
- Provide an AI-usage record with actual chat evidence or links where available.
- Include the student's AI-usage reflection.
- Use TDD and report observed failures and passes honestly.
- Include an AI co-author trailer on AI-assisted commits, preceded by two blank lines.
- Do not represent unfinished features as implemented.

The complete original rubric, reflection questions, word limit, required transcript format, and screenshot criteria remain unverified against the original brief. No extra rubric requirements are inferred here.

---

## §0. ChatGPT brainstorming session

- **Shared conversation link:** https://chatgpt.com/share/6addf90d-1d20-83ec-98a2-763aa1f8af27
- **Label / Format:** Shared conversation link (not a raw transcript export).
- **Access status:** Provided by the student. Public accessibility has not been independently verified; access depends on OpenAI/ChatGPT link sharing permissions.
- **Content scope:** Used by the student for initial assignment planning, conceptual design, and brainstorming. The original assignment brief was uploaded in that conversation rather than committed to the repository.

---

## §1. Database connection layer

Source: Codex development conversation. User message, **verbatim excerpt**:

```text
Your task is ONLY to add a minimal, tested PostgreSQL connection layer. Do not implement authentication or vehicle features yet.

Process:

1. Inspect the existing files before editing.
2. Add a focused test for a database connectivity/health function before implementing it. Use the existing test setup; avoid tests that require an unavailable database to run silently.
3. Run the test and verify it fails for the expected reason.
4. Implement the smallest clean solution using SQLAlchemy and psycopg.
5. Read the database URL from environment configuration; never hardcode credentials.
6. Ensure the connection URL works with the current root `.env` and PostgreSQL Compose configuration.
7. Rerun the new test and the existing health test.
8. Report the exact files changed, commands run, and test results. Do not claim tests passed unless you ran them.
```

Assistant progress message, **verbatim excerpt**:

```text
The test failed as expected because `app.database` does not exist yet. I'll now implement a `SELECT 1` check using SQLAlchemy and psycopg, with a five-second connection timeout and connection cleanup. Connection errors will propagate so an unavailable database cannot appear healthy.
```

Observed pytest output, **verbatim excerpt** from the failing run:

```text
E   ModuleNotFoundError: No module named 'app.database'
```

Observed pytest output, **verbatim excerpt** from the subsequent passing run:

```text
2 passed, 1 warning in 1.76s
```

---

## §2. Registration and login

Source: Codex development conversation. User message, **verbatim excerpt**:

```text
### TDD process

1. Write focused tests before implementation.
2. Run them and confirm they fail for the expected reasons.
3. Implement the minimum code required to pass.
4. Run the new tests and all existing tests.
5. Review error handling, security, and database transaction behavior.

Tests must use an isolated test database or a clearly safe test setup. Never delete or reset normal development data during testing.
```

Assistant progress message, **verbatim excerpt**:

```text
The first auth test run failed as expected: the session dependency, `get_session`, does not exist yet. The hashing, JWT, and email-validation packages installed successfully.

I'll add the database model and session setup next, then rerun the tests before adding the routes. That will let me verify that the HTTP tests fail because registration and login are still missing.
```

Observed pytest output, **verbatim excerpt** after database scaffolding but before the routes:

```text
20 failed, 1 warning in 3.17s
```

Observed pytest output, **verbatim excerpt** after implementation:

```text
20 passed, 1 warning in 3.79s
```

Observed full-suite output, **verbatim excerpt** from that implementation stage:

```text
22 passed, 1 warning in 3.66s
```

---

## §3. JWT verification dependency

Source: Codex development conversation. **Complete verbatim user message**:

```text
add JWT verification and expiry validation in a reusable authentication dependency, with tests proving that valid tokens are accepted and expired, malformed, or incorrectly signed tokens are rejected. Keep the changes limited to authentication infrastructure; don't implement vehicle endpoints yet.
```

Assistant progress message, **verbatim excerpt**:

```text
The new tests failed as expected: `get_current_user` does not exist yet. I'll implement it with a fixed HS256 algorithm and required `sub`, `iat`, and `exp` claims. It will return the user from PostgreSQL, so callers use the current database role rather than a potentially stale role in the token.
```

Observed pytest output, **verbatim excerpt** before implementation:

```text
20 deselected, 1 warning, 18 errors in 3.03s
```

Those were fixture setup/import errors for the missing dependency, not 18 assertion failures. Observed output after implementation, **verbatim excerpt**:

```text
18 passed, 20 deselected, 1 warning in 6.18s
```

Observed full-suite output, **verbatim excerpt**:

```text
40 passed, 1 warning in 8.40s
```

---

## §4. Honest documentation and missing assignment evidence

Source: Codex development conversation. User reply to a clarification question, **verbatim excerpt**:

```text
The original assignment brief was uploaded in my ChatGPT conversation, not stored in the repository. Please continue using the requirements already established in our project plan. Don't invent missing requirements or fabricate AI chat logs. If you can't access the original brief or raw chat history, tell me exactly what files or links you need from me.
```

---

## §5. Activity summary — vehicle inventory, search, frontend, migration, seeding (Codex)

*This is an editorial summary, not a raw log. The full Codex conversation transcript has not been exported or shared.*

| Stage | AI assistance | Evidence and limits |
| --- | --- | --- |
| Database foundation (`4d8731f`) | Added connection check, configuration loading, PostgreSQL connectivity test. | Missing-module failure → 2 passing tests observed (§1). |
| Authentication (`ec26313`) | Added user model, sessions, validation, Argon2 hashing, registration, login, signed tokens. | 20 failing → 20 passing auth, 22 total observed (§2, §3). |
| JWT dependency (`ec26313`) | Added `get_current_user` and a test-only protected route. | 18 setup errors → 18 passing, 40 total observed (§3). |
| Vehicle inventory (`478f1ae`) | Added Vehicle model, CRUD routes, atomic purchase/restock, and full test suite (`test_inventory.py`, `test_vehicles.py`). | Commit stat: 8 files, 646 insertions. Raw red/green output not in this record. |
| Search + storefront foundation (`43ff0fb`) | Added `vehicle_search.py`, migration, seeding, admin bootstrap, 60-row sample CSV, Phase 1 test suite, frontend scaffolding. | Commit stat: 12 files, 750+ insertions. |
| Search filter coverage (`470783f`) | Added `test_vehicle_search.py` (28 tests). | Commit stat: 1 file, 79 insertions. |
| Advanced search filters (`9a45770`) | Extended `vehicle_search.py` for trigram/partial match, ranking. | Commit stat: 1 file, 18 insertions. |
| Storefront and admin UI (`e829e15`) | Added `Dashboard.tsx`, extended `App.tsx`, browser E2E spec (`dashboard.spec.ts`). | Commit stat: 8 files, 410 insertions. |
| Git attribution correction | Reviewed and rewrote two commit message trailers after explicit user instructions. | Code trees verified unchanged. |
| Documentation (`456c270`) | Drafted README and initial PROMPTS.md from inspected source/tests and conversation evidence. | First documentation commit; 2 files, 452 insertions. |

These stages were consolidated into checkpoint commits. The Git history is not a separate red/green commit sequence per test, and these summaries do not prove test-first coverage for every helper or every possible failure mode.

---

## §6. CORS 500 header fix and regression test (Antigravity)

Source: Antigravity development session, 2026-10-25. Commit: `2b52df2`.

*This is an editorial summary from the Antigravity session. The full session transcript is stored in the local `.gemini/` directory but has not been exported.*

**Problem identified:** Starlette's `ServerErrorMiddleware` sits outside `CORSMiddleware` in the ASGI stack. Unhandled exceptions that escape `ExceptionMiddleware` are caught by `ServerErrorMiddleware`, which sends the 500 response through the outermost `send` — bypassing `CORSMiddleware`'s `send` wrapper. Result: no `Access-Control-Allow-Origin` header on HTTP 500 responses from allowed origins.

**Approach verified before implementation:** A scratch script confirmed the bug (status 500, no ACAO header). The fix was validated in isolation before editing any project file.

**Fix:** Added `_UnhandledExceptionMiddleware` (a raw ASGI class) to `backend/app/cors.py`, registered inside `configure_cors()` before `CORSMiddleware`. Starlette reverses `user_middleware` during stack build, placing it inside `CORSMiddleware`:

```
ServerErrorMiddleware → CORSMiddleware → _UnhandledExceptionMiddleware → ExceptionMiddleware → Router
```

The middleware catches `Exception`, returns `{"detail": "Internal server error"}` (no exception details), and the response flows through `CORSMiddleware`'s `send` wrapper, which injects the ACAO header for allowed origins. Disallowed origins still receive no CORS header.

**Regression tests added** to `backend/tests/test_cors.py`:
- `test_cors_headers_present_on_unexpected_server_exception` — verifies status 500, correct ACAO header, and no exception details in body.
- `test_cors_headers_absent_on_unexpected_exception_disallowed_origin` — verifies no ACAO header for a disallowed origin.

Both tests use a standalone `FastAPI()` instance with a route that raises `RuntimeError`, no production services required. Both passed immediately after implementation (24/24 total CORS tests).

---

## §7. Student AI-usage reflection — awaiting student input

**This section is incomplete. It must be written or approved by the student.**

The prompts below are suggested writing aids, not invented assignment questions and not a first-person reflection attributed to the student.

1. What did you use ChatGPT, Codex, and Antigravity for, and which decisions or work did you handle yourself?
2. What did you learn about PostgreSQL sessions, password hashing, JWT verification, and ASGI middleware stacks that you can now explain without AI assistance?
3. How did you check the suggested code? Describe the failing/passing tests and the distinction between testing a JWT library and testing an application authentication dependency.
4. What did you challenge or correct? Factual examples from this record include: adding the missing application-level JWT verifier, investigating the mistaken GitHub co-author attribution, and identifying the ASGI middleware ordering bug that caused CORS headers to be absent on 500 responses.
5. Where did AI save time, where did it create extra verification work, and what would you do differently next time?

**Student response:** Not yet provided. Replace this placeholder with your own reflection, following the original rubric's questions and word limit once supplied.

---

## Materials still needed for submission

| Needed material | What to provide | Why it is needed |
| --- | --- | --- |
| Original assignment brief | The original PDF/DOCX/text attachment, its full pasted text, or an accessible assignment URL. | Check the complete rubric, mandatory features, screenshot/transcript requirements. The ChatGPT upload is not accessible from this repository. |
| ChatGPT raw transcript export | Offline HTML/text export of the ChatGPT conversation. | A shared link has been provided (https://chatgpt.com/share/6addf90d-1d20-83ec-98a2-763aa1f8af27; labeled as a shared link, public accessibility unverified). If the rubric requires a raw offline export file, that is still needed. |
| Codex full conversation transcript | Shared chat URL or exported transcript. | The excerpts in §1–§3 are partial; full export/share link needed if complete logs are required. |
| Antigravity session transcript | Export from `.gemini/` session log or a share link. | §6 is a summary; full log exists locally but has not been exported. |
| Personal reflection | Student's own written answers. | Avoids fabricating learning, decisions, or personal experience. |
| Committed screenshots | Committed image files, or separately supplied images. | Screenshots have been copied to `docs/screenshots/` for repository tracking; verify they are included in submission artifacts. |

Before sharing exports or screenshots, remove credentials, tokens, and unrelated private material. Mark any redactions explicitly rather than presenting an edited export as untouched.

---

## Documentation coverage against the known requests

| Established request | Location | Status |
| --- | --- | --- |
| Overview, stack, all implemented features | README | Updated to reflect full implementation. |
| PostgreSQL and backend setup | README | Commands and environment requirements documented. |
| Frontend setup | README and frontend/README.md | Fully documented (React/Vite/Tailwind, local and deploy). |
| Test instructions and observed results | README and TEST_REPORT.md | Documented with actual run results. |
| Screenshots | README (screenshots section) | Genuine Playwright captures copied to tracked `docs/screenshots/` and embedded. |
| Actual AI chat evidence | Verbatim excerpts §1–§4 & ChatGPT link | Partial evidence only; shared ChatGPT link provided; full exports/links pending. |
| Student reflection | §7 | Awaiting the student; no personal account fabricated. |
| Full original assignment compliance | Not yet verifiable | Original brief must be supplied. |
