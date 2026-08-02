# Energy Grid Dashboard

*Australia's electricity-market transition, modelled end-to-end — repo codename `gridlens`.*

An analytics-engineering pipeline over Australia's **National Electricity Market (NEM)**:
public AEMO market data → a clean dimensional model in **dbt** → a forecast → a
deployed **Evidence.dev** dashboard, refreshed daily by a GitHub Actions cron.

The story: **how the rise of renewables is reshaping price, demand, and carbon intensity**
across the five NEM regions (NSW, QLD, VIC, SA, TAS).

> Portfolio project 2 of 3 — analytics-engineering lane. (Project 1, *Global Pulse*,
> is an AI/RAG news-intelligence agent.)

## Architecture

![GridLens architecture](docs/architecture.svg)

## Stack

| Layer | Choice | Why |
|---|---|---|
| **Ingestion** | Python + `httpx` (managed by `uv`) | AEMO public CSVs, no API key |
| **Warehouse** | **DuckDB** (primary) | Free, Mac-native, always-on so the live pipeline never expires |
| | **Snowflake** (verified run) | the same dbt project builds on Snowflake — 27 tests green, marts identical to DuckDB ([details](SNOWFLAKE.md)) |
| **Transform** | **dbt Core** | staging → marts, tests, docs, lineage — the centerpiece |
| **Forecast** | `statsforecast` | 7-day demand forecast per region, backtested vs a seasonal baseline |
| **Dashboard** | **Evidence.dev** (primary) | code-based BI, git-versioned, deploys free as a static site — the automated public deliverable |
| | **Power BI** (secondary) | polished report over the same marts on a Windows PC; the near-mandatory AU analyst tool; manual refresh, $0 |
| **Orchestration** | GitHub Actions cron | daily refresh of the whole chain |

## Data source (verified, honestly labelled)

Primary source is **AEMO** (Australian Energy Market Operator), the market's official
operator — public, free, and requires **no API key**.

- **Price & demand:** AEMO "Aggregated price and demand" — regional reference price
  (RRP, A$/MWh) and operational demand (MW). 5-minute from Oct 2021; 30-minute before
  the five-minute-settlement reform (normalised to a common grain in dbt).
- **Generation by fuel:** AEMO NEMWEB MMSDM `DISPATCH_UNIT_SCADA` (per-DUID 5-min; ~87M rows
  over 21 months) joined to a DUID→fuel-tech reference built from AEMO's Registration &
  Exemption List. **Utility-scale only** — excludes behind-the-meter rooftop PV.
- **Carbon intensity** is *estimated* from per-fuel emission factors (in `seed_fueltech.csv`),
  not unit-specific AEMO figures — labelled as such throughout.

> **Note on OpenNEM:** the original brief targeted OpenNEM's open API. As of June 2026 that
> project has been rebranded to **OpenElectricity** and its API now requires a *waitlisted*
> key under a non-commercial licence. GridLens therefore builds directly on the underlying
> **AEMO** public data — which is more résumé-relevant for the Australian market and keeps the
> automated refresh free of key/rate-limit risk.

Attribution: data sourced from AEMO. © AEMO. Used for non-commercial, educational purposes.

## Phases

- [x] **Phase 1 — Ingestion.** `uv` project; AEMO price & demand → DuckDB `raw` layer.
      *2.57M rows, 5 regions, Jun 2020–Jun 2026, 0 dupes / 0 nulls. Negative-price
      intervals rose 5%→18% (2020→2025); the market price cap climbed $10k→$20.3k/MWh.*
- [x] **Phase 2 — dbt modelling.** *2a:* price & demand — `fct_price_demand` (2.57M) +
      `fct_region_daily` + `dim_region`. *2b:* generation — `dim_duid`/`dim_fueltech` (from
      AEMO's registry), `fct_generation` (87M SCADA rows → region×fuel×30-min) +
      `fct_generation_daily` + `fct_region_energy_daily` (renewable share + est. carbon
      intensity). **3 seeds, 8 models, 48 tests pass**, docs + lineage.
- [x] **Phase 3 — Forecast.** `statsforecast` 7-day daily-demand forecast per region
      (`fct_demand_forecast`, +90% interval) with a rolling-origin backtest
      (`fct_forecast_accuracy`). AutoETS & MSTL beat the seasonal-naive baseline by
      **16–31%** (MAPE 3–7%).
- [x] **Phase 4 — Dashboard.** Evidence.dev (`reports/`) reading the DuckDB marts:
      Overview, Renewables, Price & Demand, Carbon, Forecast. Verified rendering in-browser.
- [x] **Phase 5 — Deploy + automate.** CI/CD built & verified: `.github/workflows/refresh.yml`
      runs the full pipeline daily and deploys to **Cloudflare Pages**; static build verified
      (196 files). One-time GitHub + Cloudflare setup in [DEPLOY.md](DEPLOY.md). *(awaiting your repo + secrets)*
- [x] **Phase 6 — Polish.** SVG architecture diagram (above), a [findings write-up](FINDINGS.md),
      and a **dbt-on-Snowflake run** — executed and verified: `PASS=27, ERROR=0`, marts
      **byte-identical to the DuckDB build**, 0.03 credits. See [SNOWFLAKE.md](SNOWFLAKE.md).

## Quickstart

```bash
# 1. Install dependencies (creates a Python 3.12 venv)
uv sync

# 2. Ingest AEMO price & demand into DuckDB (data/gridlens.duckdb)
uv run python -m gridlens.ingest_price_demand

# 3. Build the DUID->fuel seed, then ingest per-DUID generation (SCADA)
uv run python -m gridlens.build_duid_fueltech_seed
uv run python -m gridlens.ingest_generation       # ~24 months, auto-trims to MMSDM availability

# 4. Build the warehouse models (from transform/); forecast marts excluded first pass
cd transform
uv run dbt deps  --profiles-dir .                  # one-time: fetch dbt_utils
uv run dbt build --profiles-dir . --exclude fct_demand_forecast fct_forecast_accuracy

# 5. Train the demand forecast (reads marts, writes forecast.* back to DuckDB)
cd ..
uv run python -m gridlens.forecast_demand

# 6. Build everything incl. forecast marts, then docs
cd transform
uv run dbt build --profiles-dir .                  # 3 seeds, 10 models, 73 tests
uv run dbt docs generate --profiles-dir . && uv run dbt docs serve --profiles-dir .

# 7. (optional) Export marts to Parquet for the Power BI artifact
cd ..
uv run python -m gridlens.export_marts

# 8. Run the Evidence dashboard
cd reports && npm install
npm run sources    # cache the marts
npm run dev        # http://localhost:3000
```

`data/` (raw CSVs + the DuckDB file) and `.env` are gitignored; copy `.env.example`
to `.env` only when you reach the Snowflake phase.

## Repo layout

```
gridlens/
├── src/gridlens/
│   ├── config.py                    # regions, AEMO endpoints, ingest windows, paths
│   ├── ingest_price_demand.py       # AEMO price & demand → raw.price_demand
│   ├── ingest_generation.py         # NEMWEB SCADA → raw.dispatch_unit_scada
│   ├── build_duid_fueltech_seed.py  # AEMO registry xlsx → seed_duid_fueltech.csv
│   ├── forecast_demand.py           # statsforecast → forecast.* tables
│   └── export_marts.py              # marts → data/exports/*.parquet (Power BI feed)
├── transform/                       # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml                 # DuckDB (dev) target; Snowflake added in Phase 6
│   ├── models/
│   │   ├── staging/                 # stg_price_demand, stg_dispatch_scada
│   │   └── marts/                   # dims + price/demand, generation & forecast facts
│   ├── seeds/                       # seed_region, seed_fueltech, seed_duid_fueltech
│   └── macros/                      # generate_schema_name
├── reports/                         # Evidence.dev dashboard (5 pages over the marts)
│   ├── sources/gridlens/            # connection.yaml + source queries (read marts)
│   └── pages/                       # index, renewables, prices, carbon, forecast
├── data/                            # gitignored: raw CSVs + gridlens.duckdb
├── .env.example                     # Snowflake creds template (Phase 6)
└── pyproject.toml
```
