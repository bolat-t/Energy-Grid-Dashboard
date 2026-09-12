# Energy Grid Dashboard

Australia's electricity market publishes a five-minute record of itself — what power
cost, how much was used, and which generators supplied it — for every state, going back
years, for free. Almost nobody reads it. This takes six years of that record and turns it
into a picture of what the shift to renewables is actually doing to the grid.

**Live:** https://bolat-t.github.io/Energy-Grid-Dashboard/ · [data model & lineage](https://bolat-t.github.io/Energy-Grid-Dashboard/dbt/index.html) · [what I found](FINDINGS.md)

It rebuilds itself every morning from AEMO's public files.

## What it found

- Renewables are about a third of utility-scale generation and climbing. The national number
  hides how uneven that is: Tasmania is near 100% (hydro), South Australia around 75%
  (wind and sun), the three coal states bunched at a third, with Queensland moving fastest.
- **About one five-minute interval in seven cleared below $0** over six years. In 2025 South
  Australia did it 30% of the time. The states rank on that chart in almost exactly the
  order of their renewable share — nobody planned that, it falls out of the physics.
- Victoria is the dirtiest grid in the country by a wide margin, because brown coal emits a
  third more carbon than black coal per unit of power. Tasmania is effectively zero.
- Demand has been flat for six years despite population growth. The reason is on people's
  roofs, and it shows up in the data as demand that never arrives rather than as supply.
- A seven-day demand forecast lands within about 3% in the big steady states and about 7%
  in South Australia, where a grid that runs on weather is harder to predict than one that
  runs on coal. Snowflake's built-in forecasting, tested on the same hidden week, beat the
  Python model on average and lost in the two biggest states — a genuine split decision.

The longer version, with the two bugs that only showed up once it ran in the cloud, is in
[FINDINGS.md](FINDINGS.md).

## How it works

![Architecture](docs/architecture.svg)

Python pulls the raw files from AEMO into a DuckDB warehouse — a single file on disk, so a
full rebuild takes seconds and costs nothing. dbt models it into staging and marts with 68
tests attached, and a small forecasting model runs on top. A static dashboard is built from
the marts and published to GitHub Pages by a daily GitHub Actions job.

The same dbt project also builds on Snowflake. I checked, and the marts came out identical
to the DuckDB ones. The recipe is in [SNOWFLAKE.md](SNOWFLAKE.md); the in-database forecast
and anomaly results from that run are committed as seeds so they survive the trial expiring.

Two things worth knowing before trusting a number:

- Generation is **utility-scale only**. Rooftop solar is enormous in Australia and the
  market operator counts it as *reduced demand* rather than supply, so it is not in the
  generation figures.
- Carbon intensity is an **estimate** from standard emission factors per fuel
  (`transform/seeds/seed_fueltech.csv`), not AEMO's official numbers.

## Running it

```bash
uv sync                                                 # Python 3.12 venv + deps

uv run python -m energy_grid.ingest_price_demand        # AEMO price & demand, 72 months
uv run python -m energy_grid.build_duid_fueltech_seed   # generator -> fuel type, from AEMO's registry
uv run python -m energy_grid.ingest_generation          # per-generator 5-min output, ~24 months

cd transform
uv run dbt deps  --profiles-dir .
uv run dbt build --profiles-dir . --exclude fct_demand_forecast fct_forecast_accuracy
cd ..
uv run python -m energy_grid.forecast_demand            # reads the marts, writes the forecast back
cd transform && uv run dbt build --profiles-dir .       # everything, incl. forecast marts
uv run dbt docs generate --profiles-dir . --static      # self-contained docs site

cd ../reports && npm install && npm run sources && npm run dev   # dashboard on :3000
```

`data/` (raw downloads and the warehouse file) and `.env` are gitignored. The first
generation pull is slow — it back-fills a couple of years of five-minute readings for every
generator in the country — and later runs only fetch new months.

## Layout

```
src/energy_grid/         ingestion, forecasting, export, Snowflake setup
transform/               dbt project: models, seeds, tests, macros
reports/                 dashboard pages (markdown + SQL) and their source queries
docs/                    architecture diagram
.github/workflows/       the daily refresh + deploy job
```

Deployment notes are in [DEPLOY.md](DEPLOY.md).

## Data

Everything comes from the Australian Energy Market Operator's public data: the aggregated
price and demand files, and the MMSDM dispatch archive on NEMWEB for per-unit generation.
No API key is needed for any of it. © AEMO; used here for non-commercial, educational
purposes.
