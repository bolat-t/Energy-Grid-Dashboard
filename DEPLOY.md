# Deploying the Energy Grid Dashboard

The dashboard is a static Evidence.dev site. A GitHub Actions workflow
([`.github/workflows/refresh.yml`](.github/workflows/refresh.yml)) runs the full
pipeline daily and deploys to **Cloudflare Pages**:

```
ingest (AEMO) → dbt build → forecast → export → Evidence build → wrangler deploy
```

Everything below is free (GitHub public repo + Cloudflare Pages free tier).

## 1. Push the repo to GitHub

```bash
cd "gridlens"
git add -A
git commit -m "GridLens: AEMO → dbt → forecast → Evidence dashboard"
gh repo create gridlens --public --source=. --remote=origin --push
# or: create an empty public repo on github.com, then:
#   git remote add origin https://github.com/<you>/gridlens.git && git push -u origin main
```

## 2. Create the Cloudflare Pages project (once)

Either via the dashboard (Workers & Pages → Create → Pages → **Direct Upload** →
name it `gridlens`) or the CLI:

```bash
npx wrangler login
npx wrangler pages project create gridlens --production-branch main
```

This gives you `https://gridlens.pages.dev` (it can coexist with your other
Cloudflare Pages projects — the free plan allows many).

## 3. Add two GitHub repo secrets

`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Where to get it |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens → Create Token → **"Cloudflare Pages — Edit"** template |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard URL, or `npx wrangler whoami` |

## 4. Run it

`Actions → refresh → Run workflow` (manual trigger) for the first deploy, then it
runs daily on the cron. The **first run is slow (~10–15 min)** — it back-fills
~21 months of generation SCADA. Later runs reuse the cached downloads and only
fetch new months.

## Notes
- No data is committed: `data/` is gitignored and rebuilt in CI each run.
- AEMO needs no API key. `.env` (Snowflake only) stays gitignored.
- To deploy elsewhere instead (GitHub Pages / Netlify), swap the final step;
  the build output is `reports/build/`.
