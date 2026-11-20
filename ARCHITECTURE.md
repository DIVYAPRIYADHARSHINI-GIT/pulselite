# PulseLite architecture

Planned before implementation · 20 November 2026 · Asia/Kolkata

## Scope and isolation

A new, original analytics product contained entirely in this directory. Separate frontend and backend applications in one repository, with an independently tested tracker and sample website. No code, branding, or assets copied from other projects. No external account inspection or deployment without separate, explicit permission. GitHub, Vercel, and hosted database/environment-variable actions have distinct approval gates. Local SQLite creation also requires approval before execution.

## Architecture

- **Frontend:** Vite + React + TypeScript. Responsive light/dark application, original teal/ink visual identity, accessible forms, semantic tables, SVG time-series chart, install instructions, CSV export and honest demo labels. Owner authentication uses an HTTP-only session cookie, not browser-stored tokens. Only the dashboard theme may use localStorage; the tracker never does.
- **Backend:** Python + FastAPI, SQLAlchemy 2, Alembic. PostgreSQL in production; SQLite in local development/tests. Synchronous SQLAlchemy sessions are request scoped. Queries aggregate within SQL. API boundary rejects unknown fields and invalid inputs.
- **Tracker:** standalone JavaScript, less than 3,000 uncompressed bytes. One script tag, no dependencies, cookies or storage. Fetch uses `credentials: 'omit'` and `referrerPolicy: 'no-referrer'`. Sends path without query/hash, referrer hostname only, coarse screen category, pageview type and DNT signal. Backend also enforces DNT using the current owner setting. No beacon API because credentials behavior is less explicit.
- **Demo website:** original small studio/publication site served separately. Installer/test harness inserts the actual site key and tracker URL. Keys identify sites publicly and are not authentication secrets.

## Folder structure

```
pulselite/
  ARCHITECTURE.md
  README.md
  DEPLOY.md
  BUILDER_LOG.md
  FINAL_REPORT.md
  frontend/          # Vite application, component/unit tests
  backend/
    app/             # config, models, validation, privacy, auth, API, aggregation
    migrations/      # Alembic schema revisions
    tests/           # unit and API tests; SQLite and optional approved PostgreSQL
    scripts/         # seed and retention cleanup
  tracker/           # small tracker, isolated runtime tests
  demo-site/         # original example site and installation configuration
  tests/             # Chrome journey, mobile/theme/accessibility, diagnostics
  screenshots/       # actual browser captures, never fabricated
  bugs/              # immutable, numbered failure transcripts/screenshots
  reports/           # suite outputs and machine-readable check counts
```

## Data model

- **users:** id, normalized owner email, Argon2id password hash, created_at. These are owner account details, not visitor analytics. No plaintext password is retained.
- **sessions:** SHA-256 digest of a cryptographically random cookie token, user_id, expires_at. Plain session tokens exist only in cookie issuance/runtime and are never logged.
- **sites:** id, owner_id, display name, exact canonical allowed origin, random public site key, respect_dnt (default true), is_demo, created_at. Site key is public, cannot grant dashboard access.
- **events:** integer id, site_id, UTC timestamp, daily visitor HMAC, sanitized pathname, referrer hostname, source category, device category, browser family, platform-supplied country code. No IP/full UA/city/name/email columns. Client timestamps are not accepted.
- **daily_salts:** UTC date, random secret salt. Only the current day's row is retained; previous salts are deleted on rotation. These are operational secrets stored only in the authorized database, never in source/logs/reports. Random salts (not a permanently reproducible date derivation) prevent recreating earlier identifiers after rotation. A database atomic insert handles concurrent workers.
- **rate_buckets:** non-identifying opaque bucket key, minute window, count. Database-backed atomic counters work across serverless instances. Collector limits by site, and authentication limits by short-lived HMAC bucket; raw addresses never stored.

Indexes: events(site_id, occurred_at), events(site_id, path, occurred_at), events(site_id, visitor_hash, occurred_at); owner site lookup; session expiry; rate window and event timestamp for retention.

## Data flow

1. Owner signs up/signs in. Argon2id verifies password. Opaque session cookie is HTTP-only, Secure in production, expiring, with explicit SameSite policy. Unsafe owner requests require the configured dashboard Origin (CSRF defense). Owners can only access their own sites.
2. Owner adds an exact website origin. PulseLite shows one script tag. Tracker key is public; origin registration is a browser abuse barrier, not proof against forged HTTP clients. Domain ownership verification is a future hardening item.
3. Tracker posts a small JSON pageview with credentials omitted. Collector bounds the body before parsing, validates the site key and exact Origin, rate-limits, ignores known bots, and checks DNT. It sanitizes paths/referrers before persistence.
4. The backend transiently reads the transport IP and UA. On Vercel it uses only the configured trusted platform IP/header boundary; local mode does not trust arbitrary forwarded headers. HMAC-SHA256 over unambiguous IP, UA and site-key components with the day's random secret creates a visitor identifier. Inputs are never passed to ORM/loggers. Browser family is reduced to a short allowlisted value. Country is obtained only from an explicitly configured trusted hosting header; local mode defaults to unknown. No geolocation database or city.
5. SQL count, distinct count, group-by and date bucketing return daily visitors/pageviews, top pages, referrers, sources, devices, browsers, countries and five-minute active visitors. All filters and prior-period comparisons share one validated predicate builder. Date ranges use inclusive UTC civil dates translated to half-open timestamp intervals. Range capped at 366 days. Live counts use the last five minutes, independent of historical range, with selected dimension filters.
6. Frontend renders actual API values. CSV contains aggregated rows only, with spreadsheet-formula injection protection. Seed data is synthetic, clearly marked and never mixed into a non-demo site.
7. Authorized local/maintenance CLI removes old events, expired sessions, old salts and expired counters. Retention defaults to 90 days; scheduling is operator responsibility.

## Privacy and honest metrics

Daily unique visitors are approximate: same-day IP/UA changes can split a person; shared IP/UA can merge people. Multi-day visitor totals sum daily identities, not cross-day unique people. Daily hashes are pseudonymous during a day, not a guarantee of legal anonymity. UTC day rollover is intentional. URL queries/fragments and referrer paths are discarded. Pathnames can themselves contain identifying information, so sensitive sites must use anonymized routes or avoid installing the tracker. Owner emails and authentication cookies are separate from cookieless visitor collection. Hosting providers may maintain network/access logs outside application control; deployment must review those settings. Application access logging is disabled and validation errors must not echo sensitive inputs.

## Security and production constraints

Strict schemas, body caps, HTTPS production cookie, Origin checks, server-side sessions with expiry/revocation, database-backed rate limiting, SQL ownership checks, generic auth failures, parameterized SQL, no request body logs, explicit CORS policy. Public collector replies with a registered site's Origin only and never allows credentials. Dashboard origin is a separate exact allowlist. Fail startup for unsafe production settings. No production secrets downloaded locally. Env templates list names/placeholders only, no generated credentials. Tests generate passwords/tokens in memory and never include them in screenshots or outputs.

Cross-origin Vercel app/API deployments may need SameSite=None and can fail in browsers blocking third-party cookies. Preferred deployment uses frontend same-origin `/api` proxy to the backend, keeping authentication first-party while preserving separate projects. Backend deployment requires durable PostgreSQL; Vercel's ephemeral filesystem is not a production SQLite store. Free-plan limits, Python runtime support and integration steps must be verified before deployment, not assumed.

## Implementation stages and verification gates

1. **Foundation/backend:** schema and migrations, privacy functions, collector, auth, SQL stats and cleanup. Run backend SQLite unit/API tests and migration checks. Save all failures.
2. **Tracker/demo:** implement and test size, payload sanitization, DNT and credentials omission; run backend regression tests.
3. **Frontend:** home/auth/sites/install/dashboard/privacy, loading/errors/empty states, dark/mobile, filters/comparison/export. Run unit tests, typecheck and production build.
4. **Integration:** real installed Chrome, complete owner journey plus actual tracker on the demo site, SQL seed demo, live view, downloads, light/dark/mobile, axe accessibility audit and keyboard checks. Capture every requested screen and all failures. Review screenshots, not only assertions.
5. **Release (permission gated):** request GitHub permission before even checking CLI; request Vercel permission before checking CLI; request hosted DB/environment permission separately. Publish only on approved free services. Backend health first, then frontend, demo, origin configuration and live retest. Stop honestly on unsupported free-tier requirements.
6. **Handoff:** exact suite results, immutable bug evidence, screenshots with captions, experience-based Designer feedback, known limits, README and exact deployment guide. Export final report to PDF if locally supported.

## Evidence policy

Append progress and actual errors to BUILDER_LOG.md. Save numbered diagnostic transcripts under bugs without deleting/renaming prior failures. Test logs must not contain credentials or personal data. Screenshots come only from an actual browser. Clearly distinguish passed, failed, not run, blocked and unverified. No claim of PostgreSQL/live deployment testing unless actually executed with approval.
