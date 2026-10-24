# AI usage record

## Scope and evidence status

This project used OpenAI Codex for AI-assisted implementation, testing, review, Git operations, and documentation drafting. The evidence below comes from messages and tool outputs visible in the current development conversation. It is **a partial record, not a complete chat export**.

The original assignment attachment and any earlier ChatGPT conversations are not available in this repository. No shared chat URLs or transcript files have been supplied. This file does not invent links, conversations, message timestamps, or a personal reflection. It was prepared on 2026-10-24; that date is not asserted to be the timestamp of every quoted message.

Only blocks explicitly labeled **verbatim excerpt** or **complete verbatim user message** reproduce chat text. Excerpts can omit surrounding messages and tool output; each quoted block is contiguous. Other sections are editorial summaries, not raw logs. Quotes retain the wording of historical messages; they are not assertions that every historical claim remains the final state.

## Assignment requirements known from this conversation

- Provide a root README with overview, stack, setup, tests, current features, and screenshots.
- Provide an AI-usage record with actual chat evidence or links where available.
- Include the student's AI-usage reflection.
- Use TDD and report observed failures and passes honestly.
- Include an AI co-author trailer on AI-assisted commits, preceded by two blank lines, as stated by the student.
- Do not represent unfinished inventory or frontend features as implemented.

The complete original rubric, reflection questions/word limit, required transcript format, and screenshot criteria remain unverified. No extra rubric requirements are inferred here.

## Available conversation evidence

### 1. Database connection layer

Source: current development conversation. User message, **verbatim excerpt**:

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
The test failed as expected because `app.database` does not exist yet. I’ll now implement a `SELECT 1` check using SQLAlchemy and psycopg, with a five-second connection timeout and connection cleanup. Connection errors will propagate so an unavailable database cannot appear healthy.
```

Observed pytest output, **verbatim excerpt** from the failing run:

```text
E   ModuleNotFoundError: No module named 'app.database'
```

Observed pytest output, **verbatim excerpt** from the subsequent passing run:

```text
2 passed, 1 warning in 1.76s
```

### 2. Registration and login

Source: current development conversation. User message, **verbatim excerpt**:

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

I’ll add the database model and session setup next, then rerun the tests before adding the routes. That will let me verify that the HTTP tests fail because registration and login are still missing.
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

### 3. JWT verification dependency

Source: current development conversation. **Complete verbatim user message**:

```text
add JWT verification and expiry validation in a reusable authentication dependency, with tests proving that valid tokens are accepted and expired, malformed, or incorrectly signed tokens are rejected. Keep the changes limited to authentication infrastructure; don't implement vehicle endpoints yet.
```

Assistant progress message, **verbatim excerpt**:

```text
The new tests failed as expected: `get_current_user` does not exist yet. I’ll implement it with a fixed HS256 algorithm and required `sub`, `iat`, and `exp` claims. It will return the user from PostgreSQL, so callers use the current database role rather than a potentially stale role in the token.
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

### 4. Honest documentation and missing assignment evidence

Source: current development conversation. User reply to a clarification question, **verbatim excerpt**:

```text
The original assignment brief was uploaded in my ChatGPT conversation, not stored in the repository. Please continue using the requirements already established in our project plan. Don't invent missing requirements or fabricate AI chat logs. If you can't access the original brief or raw chat history, tell me exactly what files or links you need from me.
```

## Activity summary (not raw chat logs)

| Stage | AI assistance and review performed | Evidence and limits |
| --- | --- | --- |
| Database foundation | Added the connection check, configuration loading, and a PostgreSQL connectivity test. | Missing-module failure followed by two passing tests was observed. |
| Authentication | Added the user model, sessions, validation, Argon2 hashing, registration, login, and signed tokens. | Initial import error, 20 failing auth cases after scaffolding, then 20 passing auth cases and 22 passing total tests were observed. |
| Authentication review | Distinguished token creation/library checks from application-level JWT verification. | The initial implementation issued tokens but had no reusable application verifier. |
| JWT dependency | Added `get_current_user` and a test-only protected route exercising the dependency over HTTP. | Eighteen setup errors followed by 18 passing dependency cases and 40 passing total tests were observed. |
| Git attribution correction | Reviewed and changed two commit-message trailers after explicit user instructions. | Code trees were verified unchanged. The currently chosen attribution email was not independently verified as a GitHub account identity. |
| Documentation | Drafted README and this record from inspected source/tests and available conversation evidence. | The original assignment attachment and the student's final reflection remain unavailable. |

These stages were consolidated into checkpoint commits. The current Git history is not a separate red/green commit sequence, and these excerpts do not prove test-first coverage for every helper or every possible failure mode. No original red-run output file has been supplied; the excerpts above are copied from the tool outputs visible in this conversation.

## Current commit attribution

The two current checkpoint commits are:

- `4d8731f1be1730a2f7e5e8f6995d9a6d9b52ab80`: database connection and health check.
- `ec26313de80ca24a3e32dd03b1f6b7e6d825dfe7`: authentication and JWT verification.

Both currently contain the following user-selected trailer, with two blank lines before it:

```text
Co-authored-by: OpenAI Codex <codex@openai.com>
```

This records the repository's actual commit messages, **not verification that this address belongs to a particular GitHub account**. Earlier commits used a generic assignment-example address that the student reported credited an unintended account. The messages were rewritten with approval; the application and tests were preserved. No attribution configuration or Git history was changed during this documentation task.

## Student AI-usage reflection — awaiting student input

**This section is incomplete. It must be written or approved by the student.** The prompts below are suggested writing aids, not invented assignment questions and not a first-person reflection attributed to the student.

1. What did you use Codex for, and which decisions or work did you handle yourself?
2. What did you learn about PostgreSQL sessions, password hashing, and JWT verification that you can now explain without AI assistance?
3. How did you check the suggested code? Describe the failing/passing tests and the distinction between testing a JWT library and testing an application authentication dependency.
4. What did you challenge or correct? Possible factual examples from this record include adding the missing application-level JWT verifier and investigating the mistaken GitHub co-author attribution. Describe your own understanding rather than adopting an AI-written account of your experience.
5. Where did AI save time, where did it create extra verification work, and what would you do differently next time?

**Student response:** Not yet provided. Replace this placeholder with your own reflection, following the original rubric's questions and word limit once supplied.

## Materials still needed for submission

| Needed material | What to provide | Why it is needed |
| --- | --- | --- |
| Original assignment brief | The original PDF/DOCX/text attachment, its full pasted text, or an accessible assignment URL. | Check the complete rubric, mandatory features, screenshots, AI disclosure, and reflection requirements. The separate ChatGPT upload is not accessible from this repository. |
| Any separate project plan | Its file, pasted text, or accessible conversation link. | Reconcile requirements not visible in this development conversation. |
| Complete AI conversation evidence | Shared chat URL(s) accessible to the reviewer, or exported transcript text/HTML for this development conversation and any earlier ChatGPT planning sessions. | Replace or supplement partial excerpts if full logs are required. No share link can be reconstructed from the messages available here. |
| Personal reflection | Your own written answers/reflection, plus any specified word limit. | Avoid fabricating your learning, decisions, or personal experience. |
| Genuine screenshots | Image files showing the current backend/tests, and later the implemented frontend. | Populate README with real evidence rather than mockups or unfinished-feature claims. |

Before sharing exports or screenshots, remove credentials, tokens, and unrelated private material. Mark any redactions or omissions explicitly instead of presenting an edited export as an untouched complete transcript.

## Documentation coverage against the known requests

| Established request | Location | Status |
| --- | --- | --- |
| Overview, stack, implemented features | README | Covered against current code. |
| PostgreSQL and backend setup | README | Commands and environment requirements documented; a fresh installation was not rerun for this task. |
| Frontend setup | README | Explicitly pending because no frontend exists. |
| Test instructions and observed results | README and this record | Covered; full suite rerun during documentation preparation. |
| Screenshots | README | Section present; genuine images still needed. |
| Actual AI chat evidence | Verbatim excerpts above | Partial evidence only; full export/share links still needed if required. |
| Student reflection | Reflection section above | Awaiting the student; no personal account fabricated. |
| Full original assignment compliance | Not yet verifiable | Original brief must be supplied. |
