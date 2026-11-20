# PulseLite deployment guide

## Permission and free-plan boundary

GitHub, Vercel, and Neon/environment changes were separately approved. Only new PulseLite resources are in scope. Never inspect unrelated projects or existing databases. No payment details or paid plan are required for this demonstrator.

**Vercel Hobby permits personal, non-commercial use.** This deployment is a demonstration, not a commercial analytics service. If your intended use is commercial, stop: the requested free Hobby plan cannot support that use under its terms. Do not upgrade automatically.

Confirmed documentation on 20 November 2026: [Vercel Hobby](https://vercel.com/docs/plans/hobby), [Vercel limits](https://vercel.com/docs/limits), [Neon plans](https://neon.com/docs/introduction/plans). The consulted documentation states Hobby function maximum 300 seconds, 1 million invocations/month, 4 active-CPU hours and 360 GB-hours of provisioned memory. Neon Free lists 1 GB/project storage, 100 CU-hours/project/month and scale-to-zero after five idle minutes. Marketplace allowances may vary; always confirm the exact selected **Free** plan. Limits can change. No paid overage was enabled.

Cold starts can occur in both the Python function and the sleeping database. The first health/dashboard request may be slower. SQLite is **not** a durable production store on Vercel. A single-page-load tracker and 15-second polling are appropriate for a small demo, not a high-volume free-tier service.

## Resource layout

| Resource | Name / URL |
|---|---|
| GitHub account | DIVYAPRIYADHARSHINI-GIT |
| Repository requested | pulselite |
| Vercel scope | divya-6411 (Divya, Hobby) |
| Backend project | pulselite-backend / https://pulselite-backend.vercel.app |
| Frontend project | pulselite-web / https://pulselite-web.vercel.app |
| Demo project | pulselite-demo / https://pulselite-demo.vercel.app |
| New Neon resource | pulselite-postgres, Free (`free_v3`), iad1 |

The backend folder is independently deployable. Python 3.12 is pinned in `.python-version`; `index.py` exports the FastAPI app. Vercel's native FastAPI framework handles routing. Frontend and demo deploy separately. Frontend `/api/:path*` rewrites to the backend, keeping owner cookies first-party and avoiding reliance on third-party-cookie support.

## Variables (do not put secrets in source)

| Project | Variable | Value / purpose |
|---|---|---|
| Backend | `DATABASE_URL` | Secret, supplied directly by the new Neon integration. Never print or pull locally. |
| Backend build | `DATABASE_URL_UNPOOLED` | If provided by Neon, used only for disposable-schema tests; stays on hosting. |
| Backend | `PULSELITE_ENV` | `production`; rejects SQLite and non-HTTPS dashboard settings. |
| Backend | `DASHBOARD_ORIGIN` | `https://pulselite-web.vercel.app`, exact, no trailing slash. |
| Backend | `PULSELITE_BOOTSTRAP` | `1` to run Alembic inside hosting under a PostgreSQL advisory lock. |
| Backend | `PULSELITE_SEED_DEMO` | `1` seeds only if no labelled demo exists; does not reset real sites. |
| Backend | `RETENTION_DAYS` | `90` default; requires an actual scheduled cleanup command. |
| Backend | `EVENT_RATE_LIMIT` | `120` requests per site per minute, default. |
| Backend | `AUTH_RATE_LIMIT` | `20` default attempts/minute per hashed address/email bucket. |
| Backend | `VERCEL` | Hosting-provided flag; enables trust in Vercel IP/country headers. Do not enable on an untrusted proxy. |
| Frontend | `VITE_API_URL` | `/` uses the first-party `/api` proxy. Not a secret. |
| Frontend | `VITE_COLLECTOR_URL` | `https://pulselite-backend.vercel.app`. Not a secret. |
| Build command only | `PULSELITE_TEST_POSTGRES` | `1` selects isolated PostgreSQL test schemas. |

The daily salt and session tokens are generated cryptographically at runtime. No permanent analytics salt or plaintext owner password is in source, reports or environment templates. The public site key is intentionally not secret.

## Exact deployment sequence

1. **GitHub approval first.** Verify the intended account using `gh api user --jq .login`; never use a command that prints a token. In the repository only, initialize `main`, set local git name/email, inspect staged paths and secret patterns, then create a public `pulselite` repository and push. Do not read global credential files.
2. **Vercel approval separately.** Verify `vercel whoami` and `vercel teams ls`. Confirm Hobby. Create only the three new named projects. Existing projects must remain untouched.
3. **Database/environment approval separately.** For the backend project, provision the new Neon resource with the explicit free plan:

   ```sh
   vercel integration add neon --name pulselite-postgres --plan free_v3 \
     --metadata region=iad1 --metadata auth=false --environment production \
     --no-env-pull --scope divya-6411
   ```

   This command assumes the backend project is already identified to the CLI. The current CLI's `vercel link` unexpectedly downloads `.env.local` automatically. That happened once in this session; the file was deleted unread and the user notified. Avoid `link`/`env pull` for subsequent projects. Use explicit non-secret `VERCEL_PROJECT_ID` and `VERCEL_ORG_ID` to select a project for deployment. Never open any generated `.env.local`; keep it ignored, delete it, and report it.
4. Set backend non-secret configuration before deploying. `tests/configure_hosting.py` applies singleton JSON objects through `vercel api` from `hosting-config.json`; it never pulls or prints secret values. Bulk-array input returned HTTP 400 in the observed CLI, and `vercel env add` stalled after saving its first value, so those approaches were not relied on afterward.
5. Deploy **backend first** from `backend` using `vercel --prod --yes --scope divya-6411`. Hosted bootstrap executes migrations without bringing credentials locally. The configured build command runs the backend suite against temporary PostgreSQL schemas. A failing test blocks promotion; the previous healthy deployment remains available.
6. Run `.venv/bin/python tests/live_health.py https://pulselite-backend.vercel.app` from the root. Require `/health` HTTP 200 with `database: connected`, plus successful demo SQL aggregation. A successful build alone is not a successful deployment.
7. Set the two frontend build variables, check `frontend/vercel.json` points to the actual backend URL, and deploy `frontend` with its own project ID. Keep `/api` first-party; do not change SameSite to None merely to work around a broken proxy.
8. Deploy `demo-site` with its project ID. Update/confirm the backend dashboard origin and register the demo origin as a site through the owner's UI. The collector allowlist is per-site in the database, not a wildcard environment variable. Redeploy the backend after configuration changes.
9. Retest in actual Chrome: sign up, add the exact demo origin, copy the snippet, connect the public key on the demo, generate pageviews, inspect live counts and CSV, check mobile/dark/axe, and verify no CORS or unexpected console errors. Save live screenshots separately from local screenshots. List or delete all test accounts/sites.

## If a web-dashboard step is required

Do not substitute another database or upgrade. Ask the user to do these clicks:

1. Open **Vercel → Divya → pulselite-backend → Storage → Connect Database → Neon**.
2. Choose **Create New**, name **pulselite-postgres**, region **Washington, D.C. / iad1**, and select **Free**. Disable optional Neon Auth because PulseLite has its own owner authentication.
3. Connect only to **pulselite-backend**, **Production**. Verify the integration adds `DATABASE_URL` (and optionally `DATABASE_URL_UNPOOLED`) without copying its value into chat.
4. Open **Settings → Environment Variables** and add the non-secret variables in the table above. Then **Deployments → latest deployment → Redeploy**.
5. If an ordinary public production URL redirects to Vercel login, open **Settings → Deployment Protection → Vercel Authentication** and configure the production deployment to be public. Do not disclose bypass tokens. The final report states what was actually accessible.

During this session the Neon CLI provisioning succeeded; no manual integration click was needed.

## Operations and security limits

Origin checks and public site keys do not establish domain ownership or stop forged non-browser clients. Shared SQL counters prevent a cold-start reset of rate limits, but 120/minute/site is intentionally small. Known bot filtering is basic. The dashboard has no password reset, email verification, teams, billing or admin panel. Cookie sessions expire after seven days and sign-out revokes the current session.

The cleanup CLI must be scheduled by the operator in an authorized runtime. No paid scheduler is provisioned. Review provider logging/retention; the application cannot erase platform network logs. Keep `DATABASE_URL` only in the hosting integration. Do not run `vercel env pull`, read local credential stores, or commit `.env*`, `.vercel`, databases, caches or browser profiles.

Useful official references: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [rewrites](https://vercel.com/docs/rewrites), [environment variables](https://vercel.com/docs/environment-variables/managing-environment-variables), [Marketplace storage](https://vercel.com/docs/marketplace-storage).