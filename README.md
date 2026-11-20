# PulseLite

**Your traffic. Not their identity.**

An original, privacy-conscious website analytics application. React + TypeScript + Vite on the frontend; FastAPI + SQLAlchemy + Alembic on the backend; PostgreSQL in hosting and SQLite locally. A dependency-free tracker sends anonymous pageviews without cookies or browser storage.

## Applications

- Dashboard and home: https://pulselite-web.vercel.app
- Backend health: https://pulselite-backend.vercel.app/health
- Sample website: https://pulselite-demo.vercel.app
- Synthetic analytics demo: https://pulselite-web.vercel.app/demo

The public hosting is a **personal, non-commercial demonstrator on free plans**, not an offer of commercial hosting or a production SLA. See [DEPLOY.md](DEPLOY.md) and the final report for verified results and limitations.

## Repository

```
frontend/       React/TypeScript app and unit tests
backend/        FastAPI, SQLAlchemy models, Alembic migrations, API tests
tracker/        Small JavaScript tracker and isolated runtime tests
demo-site/      Original Form & Field sample website
tests/          Chrome journey, hosting helpers, diagnostic runner
screenshots/    Real local and live browser captures
bugs/           Permanent failure transcripts and screenshots
reports/        Actual suite outputs, not invented pass counts
```

The architecture was written before implementation in [ARCHITECTURE.md](ARCHITECTURE.md). [BUILDER_LOG.md](BUILDER_LOG.md) records the experience and corrections; [FINAL_REPORT.md](FINAL_REPORT.md) is the handoff.

## Local setup

Use a supported installed Python interpreter (3.11 locally tested; Vercel targets 3.12) and Node 22.12+ or a compatible newer Node. Do not use a different project's virtual environment. If a generic `python3 -m venv` chooses an unexpected base version, run the intended interpreter by its explicit path with `--copies`.

From this repository root:

```sh
python3 -m venv --copies .venv
PIP_CACHE_DIR="$PWD/.cache/pip" .venv/bin/python -m pip install -r backend/requirements.txt
npm_config_cache="$PWD/.cache/npm" PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --ignore-scripts
node tracker/build.mjs
cd frontend
npm_config_cache="$PWD/../.cache/npm" npm ci
cd ../backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m scripts.seed
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In another terminal, run `npm run dev` in `frontend`. Open **http://localhost:5173**, not the 127.0.0.1 spelling: the dashboard Origin check is exact. In a third terminal, run `.venv/bin/python tests/serve_demo.py` from the repository root and open **http://localhost:4174**. Vite proxies `/api` to port 8000. All local database files remain ignored by git.

No credentials are bundled. Sign up with your own account. The synthetic demo is public/read-only; its disabled demo-owner account has a randomly generated, undisclosed password. The seed command is idempotent for that demo site and replaces only its synthetic events.

## Install the tracker

1. Sign in, choose **My websites**, and add the exact website origin, for example `https://example.com`. Public websites require HTTPS; localhost HTTP is allowed for development.
2. Copy the generated snippet and place it before `</head>` on each page:

```html
<script defer src="https://pulselite-backend.vercel.app/api/tracker.js" data-site="YOUR_PUBLIC_SITE_KEY"></script>
```

3. Visit a page, then open the site's dashboard. The page path, not its query/fragment, is measured. The tracker also observes History API path changes and back/forward navigation.
4. To test with the included website, register `http://localhost:4174` locally or `https://pulselite-demo.vercel.app` for the hosted demo. On the sample site's connection form, paste the **public site key** and the collector base address. The key appears in the sample URL so its links keep the connection; it is not an account secret.

The tracker is **1,104 bytes uncompressed** as built. Its fetch explicitly uses `credentials: 'omit'`, `referrerPolicy: 'no-referrer'`, and no cookie/storage API. It consumes and discards the tiny collector response to complete the network request. The browser's ordinary script-download behavior is distinct from the event POST; do not place a collector on a host carrying unrelated sensitive cookies.

Do Not Track means no request by default. If an owner disables respect for DNT, the updated snippet includes `data-dnt="allow"`; reinstall it. The server still checks the site setting. Ad blockers are not bypassed.

## Privacy, precisely

Analytics stores UTC time, pathname, referrer hostname, traffic-source category, mobile/tablet/desktop category, browser family, country code or unknown, and a site-specific daily HMAC. The network IP and full user agent are read transiently to compute the HMAC and reduced browser family; they are not persisted in any database column. A fresh random secret salt is stored only for the current UTC day and older salts are removed on rotation/cleanup. Country comes only from Vercel's trusted platform header in its configured environment, never a geolocation database. No city is collected.

**Daily uniques are approximate and pseudonymous within a day.** Multi-day totals count daily identities, not cross-day unique people. Shared IP/UA can merge people and changing IP/UA can split one person. Paths may themselves contain personal information: owners must avoid installation on sensitive routes. Query stripping cannot anonymize arbitrary pathnames.

Owner emails, Argon2id password hashes and hashed session tokens are stored separately to secure the dashboard. Owner login uses an HTTP-only cookie. Production uses Secure, SameSite=Lax and a first-party API proxy. Local HTTP development omits Secure. Only the dashboard's theme may use localStorage; the tracker never does.

Application code does not log request bodies or visitor identifiers. Local access logging is disabled. Hosting providers may keep their own network/access logs; this application cannot promise otherwise. Read the in-app [privacy page](https://pulselite-web.vercel.app/privacy).

## Dashboard and API

Today/7-day/30-day/custom UTC ranges, page and dimension filters, prior-period comparisons, line chart with accessible table alternative, top pages/referrers/sources, device/browser/country breakdowns, last-five-minute activity, and aggregated CSV. Demo data is labelled in the interface. Empty, loading and error states are explicit. Dark theme persists in the dashboard only.

Core routes are `/health`, `/api/auth/signup`, `/api/auth/signin`, `/api/auth/signout`, `/api/auth/me`, `/api/sites`, `/api/sites/{id}`, `/api/sites/{id}/stats`, `/api/sites/{id}/export`, `/api/event/{public_key}`, `/api/tracker.js`, and `/api/demo/stats`. The stats API accepts `start`, `end`, `page`, `device`, `browser`, `country`, `referrer`, and `source`.

Queries aggregate in SQL and return a maximum of 20 groups per dimension (UI shows the top seven). CSV is aggregated, not a raw-event dump. A public key and exact Origin checks are abuse barriers, not proof of domain ownership or authentication of arbitrary HTTP clients. The collector caps each body at 1,024 bytes and applies database-backed per-site minute limits; default 120 requests/minute/site. Auth has its own short-lived, hashed rate buckets.

## Tests

```sh
mkdir -p tests/.tmp
cd backend
../.venv/bin/python ../tests/run_stage.py sqlite-tests ../.venv/bin/python -m pytest -q --basetemp=../tests/.tmp/pytest
cd ..
python3 tests/run_stage.py tracker-tests node --test tracker/tracker.test.mjs
cd frontend
python3 ../tests/run_stage.py frontend-unit npm test
python3 ../tests/run_stage.py frontend-build npm run build
npm run preview
# In another terminal from the root, with backend and demo also running:
python3 tests/run_stage.py chrome-tests node tests/browser.mjs
```

The Chrome harness uses the installed Google Chrome executable on this Mac; change the explicit executable path for another platform. Browser passwords are generated in memory, never printed or saved. Tests use clearly named `chrome-test-…@pulselite.test` accounts and `CHROME TEST · Form & Field` sites. The report lists/cleans test data. Browser audits use axe-core; automated results are not a complete accessibility certification.

Hosted PostgreSQL testing uses the Vercel build environment, not a downloaded database URL. Each API test receives a fresh `pulselite_test_…` schema and drops it in teardown. Pure unit tests also use isolated in-memory SQLite. See the actual deployment transcript before assuming a hosted suite passed.

## Retention and limits

From the backend directory, run `python -m scripts.cleanup` with the correctly configured authorized environment. It removes events older than `RETENTION_DAYS` (default 90), expired sessions, stale salts and counters. Schedule it in your own authorized maintenance environment; **a configured retention value alone does not run a cleanup job**.

Not implemented: password reset/email verification, team roles, domain-ownership challenges, account deletion UI, billing, bot-proof collection, long-term rollups, per-visitor sessions, campaign query tracking, consent-management integrations, or a high-traffic SLA. No claims of legal compliance or perfect anonymity are made.