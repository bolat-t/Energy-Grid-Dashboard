# Deploying the Energy Grid Dashboard

The dashboard is a static Evidence.dev site. A GitHub Actions workflow
([`.github/workflows/refresh.yml`](.github/workflows/refresh.yml)) runs the full
pipeline daily and publishes it:

```
ingest (AEMO) → dbt build → forecast → export → dbt docs → Evidence build → deploy
```

Everything here is free (public GitHub repo + Pages).

## Current setup — already live ✅

| | |
|---|---|
| Repo | https://github.com/bolat-t/gridlens |
| Dashboard | https://bolat-t.github.io/gridlens/ |
| dbt docs | https://bolat-t.github.io/gridlens/dbt/index.html |

**GitHub Pages** is enabled with *GitHub Actions* as the source, so no secrets or extra
accounts are needed. The workflow runs daily at ~04:30 AEST, and can be triggered any time
with `Actions → refresh → Run workflow` (or `gh workflow run refresh`).

> Because Pages serves the site from `/gridlens`, the workflow appends
> `deployment.basePath` to `evidence.config.yaml` before building. Without it every asset
> URL 404s.

The **first run takes ~10–15 min** (it back-fills ~21 months of generation SCADA). Later
runs restore the `data/raw` cache and only fetch new months.

## Optional — also publish to Cloudflare Pages

The workflow already contains the Cloudflare steps; they **skip automatically** unless
`CLOUDFLARE_API_TOKEN` is set, so nothing breaks by ignoring this.

To enable it and get a `gridlens.pages.dev` URL:

1. Create the project (once):

```bash
npx wrangler login
npx wrangler pages project create gridlens --production-branch main
```

2. Add two repo secrets — `Settings → Secrets and variables → Actions`:

| Secret | Where to get it |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens → Create Token → **"Cloudflare Pages — Edit"** template |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard URL, or `npx wrangler whoami` |

The workflow then builds twice — once with the base path for Pages, once at the root path
for Cloudflare — and deploys to both.

## Notes
- No data is committed: `data/` is gitignored and rebuilt in CI each run.
- AEMO needs no API key. `.env` (Snowflake only) stays gitignored and untracked.
- The Snowflake ML results are committed as dbt seeds, so the dashboard keeps working
  after the Snowflake trial lapses (see [SNOWFLAKE.md](SNOWFLAKE.md)).
