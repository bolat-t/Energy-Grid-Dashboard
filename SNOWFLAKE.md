# Snowflake credibility run (optional)

GridLens runs on **DuckDB** for free, always-on. This is a one-time demonstration that
the same dbt project also builds on **Snowflake** (during its 30-day, $400 trial) — so the
résumé can honestly say *"dbt on Snowflake and DuckDB."*

We run the **price & demand vertical**, which uses only portable SQL:
`seed_region → dim_region`, `stg_price_demand → fct_price_demand → fct_region_daily`.

> The generation models stay on DuckDB: `fct_generation` uses DuckDB's `time_bucket()`
> (Snowflake's equivalent is `TIME_SLICE`). Swapping it is the only change needed to run the
> full project on Snowflake — left as a deliberate, documented boundary.

## 1. Install the adapter

```bash
uv add dbt-snowflake
```

## 2. Create Snowflake objects (Snowsight, as ACCOUNTADMIN)

```sql
create warehouse if not exists gridlens_wh
  warehouse_size = xsmall auto_suspend = 60 auto_resume = true initially_suspended = true;
create database if not exists gridlens;
create schema   if not exists gridlens.raw;

-- spend guard: suspend at 90% of a 50-credit monthly quota
create resource monitor if not exists gridlens_rm
  with credit_quota = 50 frequency = monthly start_timestamp = immediately
  triggers on 90 percent do suspend;
alter warehouse gridlens_wh set resource_monitor = gridlens_rm;
```

## 3. Load raw price & demand from Parquet

```bash
uv run python -m gridlens.export_marts        # writes data/exports/raw_price_demand.parquet
```

Then with SnowSQL (`PUT` isn't available in the web UI):

```sql
create or replace stage gridlens.raw.load_stage file_format = (type = parquet);
-- in SnowSQL:
--   put file://data/exports/raw_price_demand.parquet @gridlens.raw.load_stage;

create or replace table gridlens.raw.price_demand (
  region varchar, settlement_date timestamp_ntz, total_demand_mw double,
  rrp_aud_mwh double, period_type varchar, source_month varchar, source_file varchar
);
copy into gridlens.raw.price_demand from @gridlens.raw.load_stage
  file_format = (type = parquet) match_by_column_name = case_insensitive;
```

## 4. Point dbt at Snowflake

Fill the `SNOWFLAKE_*` vars in `.env` (template in `.env.example`; use `ACCOUNTADMIN` for
`SNOWFLAKE_ROLE` on a fresh trial), then load them and build:

```bash
set -a && source .env && set +a
cd transform
uv run dbt build --profiles-dir . --target snowflake \
  --select seed_region dim_region stg_price_demand fct_price_demand fct_region_daily
uv run dbt docs generate --profiles-dir . --target snowflake
```

Capture for the portfolio: the green `dbt build` against Snowflake, the lineage graph from
`dbt docs`, and a Snowsight screenshot of `GRIDLENS.MARTS.FCT_REGION_DAILY`.

## 5. Stop the meter

The XS warehouse auto-suspends after 60 s. When you're done: `alter warehouse gridlens_wh suspend;`
(or just let the trial lapse). The live DuckDB pipeline is unaffected.
