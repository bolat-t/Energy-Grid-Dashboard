# Snowflake credibility run (optional)

The pipeline runs on **DuckDB** for free, always-on. This is a one-time demonstration that
the same dbt project also builds on **Snowflake** (during its 30-day, $400 trial) — so the
résumé can honestly say *"dbt on Snowflake and DuckDB."*

We run the **price & demand vertical**, which uses only portable SQL:
`seed_region → dim_region`, `stg_price_demand → fct_price_demand → fct_region_daily`.

> The generation models stay on DuckDB: `fct_generation` uses DuckDB's `time_bucket()`
> (Snowflake's equivalent is `TIME_SLICE`). Swapping it is the only change needed to run the
> full project on Snowflake — left as a deliberate, documented boundary.

**Already done for you:** `dbt-snowflake` is installed, `transform/profiles.yml` has a
`snowflake:` target reading env vars, and `.env` exists (gitignored) ready for values.

## 1. Get a trial account

Sign up at [signup.snowflake.com](https://signup.snowflake.com) — 30 days, $400 credits, no
card. Pick **AWS** and a region near you (e.g. `ap-southeast-2` Sydney).

## 2. Fill in `.env`

```
SNOWFLAKE_ACCOUNT=ABCDEFG-XY12345
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

Find `SNOWFLAKE_ACCOUNT` in Snowsight: bottom-left account menu → **View account details** →
*Account Identifier* (format `ORGNAME-ACCOUNTNAME`).

> `.env` is gitignored — credentials never reach the repo. Nothing else in the project needs them.

## 3. Create everything + load the data (one command)

```bash
uv run python -m gridlens.export_marts      # if data/exports/ isn't fresh
uv run python -m gridlens.setup_snowflake
```

This creates the warehouse (XSMALL, auto-suspend 60 s), the `GRIDLENS` database and `RAW`
schema, a **resource monitor** capping usage at 50 credits/month, then loads ~2.57M rows of
raw price & demand and verifies the count. It's idempotent — safe to re-run.

## 4. Build with dbt against Snowflake

```bash
set -a && source .env && set +a
uv run dbt build --project-dir transform --profiles-dir transform --target snowflake \
  --select seed_region dim_region stg_price_demand fct_price_demand fct_region_daily
uv run dbt docs generate --project-dir transform --profiles-dir transform --target snowflake
```

Capture for the portfolio: the green `dbt build` against Snowflake, the lineage graph from
`dbt docs`, and a Snowsight screenshot of `GRIDLENS.MARTS.FCT_REGION_DAILY`.

## 5. Stop the meter

The XS warehouse auto-suspends after 60 s of idle, and the resource monitor is a hard backstop.
When you're done:

```sql
alter warehouse gridlens_wh suspend;
```

Or just let the trial lapse — the live DuckDB pipeline is completely unaffected.
