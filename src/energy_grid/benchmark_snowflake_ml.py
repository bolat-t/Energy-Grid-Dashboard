"""Benchmark Snowflake ML FORECAST against the Python statsforecast models.

Fair comparison by construction: both engines train on the *same* history and
predict the *same* held-out 7 days, then are scored against the same actuals.

  train  = every complete day up to (last_day - 7)
  holdout= the final 7 days
  models = SNOWFLAKE.ML.FORECAST (multi-series, one model for all 5 regions)
           vs AutoETS / MSTL / SeasonalNaive (statsforecast, local)

Note this is a single-origin holdout, which is a different (simpler) protocol
than the 6-window rolling backtest behind fct_forecast_accuracy — the numbers
here are comparable to each other, not to that table.

Writes results to DuckDB `forecast.engine_benchmark` for dbt/the dashboard.

Run: uv run python -m energy_grid.benchmark_snowflake_ml
"""

from __future__ import annotations

import os
import sys

import duckdb
import numpy as np
import pandas as pd

from energy_grid import config
from energy_grid.setup_snowflake import load_dotenv

HORIZON = 7


def _metrics(actual: pd.Series, pred: pd.Series) -> dict[str, float]:
    err = actual - pred
    return {
        "mae": round(float(err.abs().mean()), 1),
        "rmse": round(float(np.sqrt((err**2).mean())), 1),
        "mape": round(float((err.abs() / actual * 100).mean()), 2),
    }


def main() -> None:
    load_dotenv(config.PROJECT_ROOT / ".env")
    if not os.environ.get("SNOWFLAKE_ACCOUNT"):
        sys.exit("No Snowflake credentials in .env — see SNOWFLAKE.md")

    # --- pull the shared series from DuckDB (identical to what's in Snowflake) ---
    ddb = duckdb.connect(str(config.DUCKDB_PATH))
    hist = ddb.execute(
        """
        select region, settlement_day as ds, avg_demand_mw as y
        from marts.fct_region_daily
        where interval_count >= 40
        order by region, settlement_day
        """
    ).df()
    hist["ds"] = pd.to_datetime(hist["ds"])

    last_day = hist["ds"].max()
    cutoff = last_day - pd.Timedelta(days=HORIZON)
    train = hist[hist["ds"] <= cutoff]
    holdout = hist[hist["ds"] > cutoff]

    print("Engine benchmark — Snowflake ML vs Python statsforecast")
    print(f"  train  : {train['ds'].min().date()} .. {cutoff.date()} ({len(train):,} rows)")
    print(f"  holdout: {(cutoff + pd.Timedelta(days=1)).date()} .. {last_day.date()} "
          f"({len(holdout):,} rows, {HORIZON} days x 5 regions)\n")

    results: list[dict] = []

    # ---------------- Snowflake ML FORECAST ----------------
    import snowflake.connector

    print("training SNOWFLAKE.ML.FORECAST (multi-series)...")
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "ENERGY_GRID_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "ENERGY_GRID"),
        schema="MARTS",
    )
    cur = con.cursor()
    try:
        cur.execute(
            f"""
            create or replace view ml_train as
            select region, to_timestamp_ntz(settlement_day) as ts, avg_demand_mw as y
            from energy_grid.marts.fct_region_daily
            where interval_count >= 40
              and settlement_day <= date '{cutoff.date()}'
            """
        )
        cur.execute(
            """
            create or replace snowflake.ml.forecast demand_fc(
                input_data => system$reference('view','ml_train'),
                series_colname => 'REGION',
                timestamp_colname => 'TS',
                target_colname => 'Y')
            """
        )
        cur.execute(f"call demand_fc!forecast(forecasting_periods => {HORIZON})")
        rows = cur.fetchall()
        cols = [d[0].lower() for d in cur.description]
        sf = pd.DataFrame(rows, columns=cols)
        # SERIES comes back as a JSON-quoted variant, e.g. "NSW1"
        sf["region"] = sf["series"].astype(str).str.strip('"')
        sf["ds"] = pd.to_datetime(sf["ts"]).dt.normalize()
        sf = sf[["region", "ds", "forecast"]].rename(columns={"forecast": "pred"})
        print(f"  got {len(sf)} predictions")
    finally:
        cur.execute("drop view if exists ml_train")
        cur.execute("alter warehouse "
                    f"{os.environ.get('SNOWFLAKE_WAREHOUSE','ENERGY_GRID_WH')} suspend")
        cur.close()
        con.close()

    merged = holdout.merge(sf, on=["region", "ds"], how="inner")
    if len(merged) != len(holdout):
        print(f"  ! matched {len(merged)}/{len(holdout)} holdout rows")
    for region, g in merged.groupby("region"):
        results.append({"region": region, "engine": "Snowflake ML",
                        "model": "SNOWFLAKE.ML.FORECAST", **_metrics(g["y"], g["pred"])})

    # ---------------- Python statsforecast ----------------
    print("\ntraining statsforecast models on the same split...")
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS, MSTL, SeasonalNaive

    sf_train = train.rename(columns={"region": "unique_id"})[["unique_id", "ds", "y"]]
    engine = StatsForecast(
        models=[SeasonalNaive(season_length=7), AutoETS(season_length=7),
                MSTL(season_length=[7, 365])],
        freq="D", n_jobs=1,
    )
    fc = engine.forecast(df=sf_train, h=HORIZON)
    fc = fc.rename(columns={"unique_id": "region"})
    fc["ds"] = pd.to_datetime(fc["ds"]).dt.normalize()

    for model in ["SeasonalNaive", "AutoETS", "MSTL"]:
        m = holdout.merge(fc[["region", "ds", model]], on=["region", "ds"], how="inner")
        for region, g in m.groupby("region"):
            results.append({"region": region, "engine": "Python", "model": model,
                            **_metrics(g["y"], g[model])})

    bench = pd.DataFrame(results)
    bench["holdout_start"] = (cutoff + pd.Timedelta(days=1)).date().isoformat()
    bench["holdout_end"] = last_day.date().isoformat()

    # ---------------- persist + report ----------------
    # Written as a dbt seed (not just a DuckDB table) so the result survives the
    # Snowflake trial and the CI rebuild, which recreates the warehouse from scratch.
    seed = config.PROJECT_ROOT / "transform" / "seeds" / "seed_engine_benchmark.csv"
    bench.to_csv(seed, index=False)
    print(f"\nwrote {seed.relative_to(config.PROJECT_ROOT)} ({len(bench)} rows)")
    ddb.close()

    print("\nMAPE % on the held-out 7 days (lower is better)\n")
    pivot = bench.pivot_table(index="region", columns="model", values="mape")
    order = [c for c in ["SNOWFLAKE.ML.FORECAST", "AutoETS", "MSTL", "SeasonalNaive"]
             if c in pivot.columns]
    print(pivot[order].to_string())

    print("\nwinner per region:")
    for region, g in bench.groupby("region"):
        best = g.loc[g["mape"].idxmin()]
        print(f"  {region:>5}: {best['model']:<22} ({best['engine']}) MAPE {best['mape']}%")

    overall = bench.groupby(["engine", "model"])["mape"].mean().sort_values()
    print("\naverage MAPE across regions:")
    for (eng, model), v in overall.items():
        print(f"  {model:<22} ({eng:<12}) {v:.2f}%")


if __name__ == "__main__":
    main()
