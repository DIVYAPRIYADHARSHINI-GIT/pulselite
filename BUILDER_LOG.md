# PulseLite — builder experience log

All entries use Asia/Kolkata dates. Failure evidence is append-only in `bugs/`; successful reruns never erase earlier attempts. No credentials are recorded.

## 20 November 2026 · Stage 0 — architecture and permission

- Created ARCHITECTURE.md before writing any code, using the scoped file tool without inspecting neighboring projects.
- User explicitly approved local SQLite, project-local dependency installation and installed Python/Node/Chrome for testing. No approval for GitHub, Vercel or hosted databases yet.
- Local runtime check succeeded: Python 3.11.15, Node 26.13.1, npm 11.20.0 and installed Google Chrome available.
- Architecture decisions: actual random daily salt with removal of older salts; database-backed collector limiting rather than a per-process dictionary; SQL-only aggregation; first-party API proxy for production session reliability. These add implementation work but avoid misleading privacy/serverless claims.
- Designer file tools created the isolated directory directly. No other project opened or modified. No error encountered so far.

### 20261120-095657-865260 — failure: stage1-install

Command exited 1. Full original diagnostic saved in bugs/20261120-095657-865260-stage1-install-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-095813-621125 — failure: stage1-backend-tests

Command exited 1. Full original diagnostic saved in bugs/20261120-095813-621125-stage1-backend-tests-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-095830-832735 — failure: dependency-audit

Command exited 1. Full original diagnostic saved in bugs/20261120-095830-832735-dependency-audit-FAILURE.txt. Investigation and fix follow; evidence retained.

## 20 November 2026 · Stages 1–2 results

- Dependency installation initially created a Python 3.15 environment despite the available command reporting Python 3.11. The pinned psycopg wheel was unavailable for 3.15. Fixed by recreating only the project virtualenv with the explicitly verified Python 3.11 executable and `--copies`. Retry installed successfully.
- The first backend suite had 4 passes and 45 setup errors: pytest's custom base-temp parent did not exist. Created `tests/.tmp` inside PulseLite (not system temp); rerun: **49 passed**, no failures. A third-party AnyIO alias deprecation warning remains non-blocking.
- npm reported a high-severity Playwright browser-download certificate advisory. Original audit preserved. Updated Playwright 1.51.1 to 1.65.1; reinstall: **0 npm vulnerabilities**. No Playwright browser download occurred; the suite uses installed Chrome.
- Tracker suite: **12 passed**, no failures. Generated backend copy is **1,086 uncompressed bytes**. Tests trap cookie/storage access, verify explicit credentials omission, DNT, referrer stripping and SPA path handling.
- Alembic upgrade succeeded against the approved local SQLite database. Alembic schema check: no drift. Seed script inserted **5,719 synthetic events** across 30 UTC days into a clearly marked demo site.
- Designer's parallel background tasks let dependency installs and database verification run independently. The append-only command wrapper reliably retained the actual first failures; failures were not overwritten by retries.
- Frontend work uses an original restrained teal/ink identity, semantic HTML, responsive layouts, custom SVG trend charts with an accessible data table, and explicit demo/privacy copy. No external imagery/font download or other project's code was needed.

### 20261120-100229-904324 — failure: frontend-audit

Command exited 1. Full original diagnostic saved in bugs/20261120-100229-904324-frontend-audit-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-100232-505133 — failure: stage3-build

Command exited 1. Full original diagnostic saved in bugs/20261120-100232-505133-stage3-build-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-100417-745912 — failure: stage4-chrome

Command exited 1. Full original diagnostic saved in bugs/20261120-100417-745912-stage4-chrome-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-100503-076438 — failure: stage4-chrome-retry

Command exited 1. Full original diagnostic saved in bugs/20261120-100503-076438-stage4-chrome-retry-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-100509-553364 — failure: backend-audit

Command exited 1. Full original diagnostic saved in bugs/20261120-100509-553364-backend-audit-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-104944-668648 — failure: stage4-chrome-timeouts

Command exited 1. Full original diagnostic saved in bugs/20261120-104944-668648-stage4-chrome-timeouts-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105221-370032 — failure: stage5-backend-config

Command exited 1. Full original diagnostic saved in bugs/20261120-105221-370032-stage5-backend-config-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105317-580130 — failure: stage4-chrome-instrumented

Command exited 1. Full original diagnostic saved in bugs/20261120-105317-580130-stage4-chrome-instrumented-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105442-016123 — failure: stage4-chrome-network-diagnostic

Command exited 1. Full original diagnostic saved in bugs/20261120-105442-016123-stage4-chrome-network-diagnostic-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105603-203624 — failure: stage4-chrome-patched-runtime

Command exited 1. Full original diagnostic saved in bugs/20261120-105603-203624-stage4-chrome-patched-runtime-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105718-692456 — failure: stage4-chrome-keepalive-fix

Command exited 1. Full original diagnostic saved in bugs/20261120-105718-692456-stage4-chrome-keepalive-fix-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105815-183517 — failure: stage4-chrome-response-drain

Command exited 1. Full original diagnostic saved in bugs/20261120-105815-183517-stage4-chrome-response-drain-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105912-291428 — failure: stage4-chrome-metric-waits

Command exited 1. Full original diagnostic saved in bugs/20261120-105912-291428-stage4-chrome-metric-waits-FAILURE.txt. Investigation and fix follow; evidence retained.

### 20261120-105920-214356 — failure: stage5-postgres-build

Command exited 1. Full original diagnostic saved in bugs/20261120-105920-214356-stage5-postgres-build-FAILURE.txt. Investigation and fix follow; evidence retained.

## 20 November 2026 · Stage 3–5 investigation and results, through 11:02 IST

- Frontend unit suite passed all 18 tests. The first production build failed because an unnecessary empty data-URL CSS import was treated as a file by PostCSS. Removed that import; TypeScript and Vite builds pass.
- npm audit found three dev-tool vulnerabilities (Vitest/tinypool/mocker). Upgraded Vitest to 5.1.1; the patched install reported no vulnerabilities. Python audit found 19 advisory entries across four packages (some duplicated identifiers). Upgraded FastAPI, Starlette, pytest, pip and setuptools; repeat audit: no known vulnerabilities. Backend regression remained 53/53 passing. Python 3.12 emits utcnow deprecation warnings; these are not hidden.
- Chrome/axe caught home-page feature numbers at 2.46:1 contrast and an inline privacy link distinguishable only by color. Adjusted the subtle light-theme token and underlined inline links. Subsequent local audits pass.
- A source review caught the Direct-referrer row removing its own filter instead of filtering empty stored referrers. Added a server mapping and regression test; Chrome later verified the fix.
- Browser checks initially raced React rendering: an assertion said the empty state was missing even though the saved screenshot showed it; later a metric assertion read zero just before the screenshot showed 2 pageviews/1 visitor. Changed these assertions to wait for the expected semantic element/value. This is recorded as harness timing, not product failure.
- Two browser runs stalled and were stopped; both have permanent transcripts. Added a per-check watchdog and streamed command output. Instrumentation then isolated a stalled keepalive response-body wait. Initial assumption that this was only DevTools instrumentation was incomplete: networkidle also failed. Consuming/discarding the response text in the tracker resolved actual request completion. Tracker grew from 1,086 to **1,104 bytes**, still under 3,000; its 12 tests pass. Complete actual request headers showed no Cookie or Referer, and SQL-backed dashboard counts proved events persisted.
- A genuine rapid-interaction bug reintroduced a cleared page filter when the next date-range change used an older router snapshot. Read current URL search state inside mutation handlers. The unchanged fast browser sequence now passes.
- User separately approved GitHub, Vercel, and a new Neon Free database/hosting variables. Verified GitHub DIVYAPRIYADHARSHINI-GIT and Vercel divya-6411 on Hobby. Set git identity locally only.
- Vercel link automatically created .env.local. Deleted it unread, kept it ignored, and told the user. Future project selection uses non-secret project IDs instead of link/env pull. Neon Free provisioned successfully without env pull; no manual web-dashboard click was needed.
- The first env-add command saved one variable but stalled; first backend deploy therefore had incomplete config and /health returned HTTP 500. Preserved the diagnostic. Bulk JSON API input then returned 400; singleton JSON via stdin succeeded. Redeployed; public /health returned 200 with a real DB query and the demo SQL aggregation returned 5,719 synthetic views.
- Backend, frontend and demo deployed separately in that order. No paid plan/payment information was used. Public deployment is a non-commercial demonstrator; Hobby is not suitable for a commercial service under its terms.
- Hosted PostgreSQL suite initially failed (5 passes, 3 failures, 45 setup errors): pooled/startup-option connections eventually reported unreachable IPv6. Used the direct Neon connection and resolved IPv4 while retaining TLS hostname identity. Retry ran **53 tests passing** in 24.74 seconds inside Vercel; every fixture schema is dropped in teardown, and no DB credential left hosting. There were 437 repeated Python 3.12 deprecation warnings, not 437 separate defects.
- Final local Chrome journey at this checkpoint: **20 passed, 0 failed; 12 axe page audits with no violations; zero unexpected console errors/network failures**. Real browser screenshots captured all requested states and were visually reviewed through Designer, including light/dark dashboards and phone layout. Live journey and final documentation remain to be verified.
- Experience: asynchronous tasks plus real screenshots made debugging possible, but initially buffered output hid progress during stalls. Timestamps are easy to miscopy: one screenshot inspection produced ENOENT; a scoped glob corrected the exact path, and that tool error was retained. No neighboring project was opened or modified.

### 20261120-110404-703376 — failure: stage6-extra-browser

Command exited 1. Full original diagnostic saved in bugs/20261120-110404-703376-stage6-extra-browser-FAILURE.txt. Investigation and fix follow; evidence retained.
