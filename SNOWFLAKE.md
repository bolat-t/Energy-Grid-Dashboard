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
uv run python -m energy_grid.export_marts      # if data/exports/ isn't fresh
uv run python -m energy_grid.setup_snowflake
```

This creates the warehouse (XSMALL, auto-suspend 60 s), the `ENERGY_GRID` database and `RAW`
schema, a **resource monitor** capping usage at 50 credits/month, then loads ~2.57M rows of
raw price & demand and verifies the count. It's idempotent — safe to re-run.

## 4. Build with dbt against Snowflake

```bash
set -a && source .env && set +a
uv run dbt build --project-dir transform --profiles-dir transform --target snowflake \
  --indirect-selection=cautious \
  --select seed_region dim_region stg_price_demand fct_price_demand fct_region_daily
uv run dbt docs generate --project-dir transform --profiles-dir transform --target snowflake
```

> `--indirect-selection=cautious` matters. By default dbt is *eager*: it also runs
> `relationships` tests belonging to the generation/forecast models (which reference
> `dim_region` but don't exist on Snowflake), and those 5 tests fail. Cautious mode runs
> only tests whose parents are all selected.

Capture for the portfolio: the green `dbt build` against Snowflake, the lineage graph from
`dbt docs`, and a Snowsight screenshot of `ENERGY_GRID.MARTS.FCT_REGION_DAILY`.

## Verified result (run 2 Aug 2026)

The trial has since expired and the warehouse with it. The forecast and anomaly results
from this run are committed as dbt seeds, so the dashboard keeps working without it.

`dbt build --target snowflake` → **PASS=27, ERROR=0** (1 seed, 1 view, 3 tables, 22 tests).

| Object | Rows |
|---|---|
| `ENERGY_GRID.RAW.PRICE_DEMAND` | 2,570,640 |
| `ENERGY_GRID.STAGING.STG_PRICE_DEMAND` | view |
| `ENERGY_GRID.MARTS.FCT_PRICE_DEMAND` | 2,570,640 |
| `ENERGY_GRID.MARTS.FCT_REGION_DAILY` | 10,960 |
| `ENERGY_GRID.MARTS.DIM_REGION` | 5 |

The marts were diffed against the DuckDB build — 2025 rows per region, average RRP,
negative-price share and peak demand are **identical on both warehouses**. Total cost:
**0.0264 credits** (a few cents).

### Gotcha worth knowing

Loading pandas `datetime64[ns]` through `write_pandas` into a `TIMESTAMP_NTZ` column makes
Snowflake read the epoch value at the wrong scale — dates land in the year ~52,000,000.
`setup_snowflake.py` avoids this by landing `settlement_date` as text and casting with
`TO_TIMESTAMP_NTZ` server-side.

## 5. Stop the meter

The XS warehouse auto-suspends after 60 s of idle, and the resource monitor is a hard backstop.
When you're done:

```sql
alter warehouse energy_grid_wh suspend;
```

Or just let the trial lapse — the live DuckDB pipeline is completely unaffected.
