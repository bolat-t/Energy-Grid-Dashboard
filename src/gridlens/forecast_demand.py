"""Phase 3 — 7-day-ahead daily demand forecast per NEM region.

Reads modelled daily demand (marts.fct_region_daily) from DuckDB, backtests
several statsforecast models with a rolling origin against a seasonal-naive
baseline, then writes back to DuckDB:
  * forecast.demand_forecast   — next 7 days per region per model (+ 90% interval)
  * forecast.forecast_accuracy — backtest MAE / RMSE / MAPE per region per model

dbt then serves these as marts (fct_demand_forecast, fct_forecast_accuracy), so
the run order in the pipeline is: dbt build -> this script -> dbt build.

Run: uv run python -m gridlens.forecast_demand
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, MSTL, SeasonalNaive

from gridlens import config

HORIZON = 7  # days ahead
N_WINDOWS = 6  # rolling-origin backtest windows (each HORIZON days)


def load_daily_demand(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        """
        select region as unique_id,
               settlement_day as ds,
               avg_demand_mw as y
        from marts.fct_region_daily
        where interval_count >= 40   -- drop partial boundary days
        order by region, settlement_day
        """
    ).df()
    df["ds"] = pd.to_datetime(df["ds"])
    return df


def main() -> None:
    con = duckdb.connect(str(config.DUCKDB_PATH))
    df = load_daily_demand(con)
    print(
        f"daily demand series: {df['unique_id'].nunique()} regions, "
        f"{len(df):,} rows, {df['ds'].min().date()} -> {df['ds'].max().date()}"
    )

    models = [
        SeasonalNaive(season_length=7),                              # baseline
        AutoETS(season_length=7),                                    # weekly + level/trend
        MSTL(season_length=[7, 365]),  # weekly + annual; default non-seasonal trend
    ]
    sf = StatsForecast(models=models, freq="D", n_jobs=1)

    # --- rolling-origin backtest -----------------------------------------
    print(f"\nbacktesting (h={HORIZON}, {N_WINDOWS} windows, step={HORIZON})...")
    cv = sf.cross_validation(df=df, h=HORIZON, n_windows=N_WINDOWS, step_size=HORIZON)
    names = [c for c in cv.columns if c not in ("unique_id", "ds", "cutoff", "y")]

    rows = []
    for name in names:
        err = cv["y"] - cv[name]
        tmp = pd.DataFrame(
            {
                "region": cv["unique_id"].to_numpy(),
                "ae": err.abs().to_numpy(),
                "se": (err**2).to_numpy(),
                "ape": (err.abs() / cv["y"] * 100).to_numpy(),
            }
        )
        agg = tmp.groupby("region").agg(mae=("ae", "mean"), mse=("se", "mean"), mape=("ape", "mean"))
        for region, r in agg.iterrows():
            rows.append(
                {
                    "region": region,
                    "model": name,
                    "mae": round(float(r.mae), 1),
                    "rmse": round(float(np.sqrt(r.mse)), 1),
                    "mape": round(float(r.mape), 2),
                    "n_windows": N_WINDOWS,
                    "horizon": HORIZON,
                }
            )
    accuracy = pd.DataFrame(rows)

    # --- final 7-day forecast with 90% prediction interval ---------------
    print("fitting final models + forecasting next 7 days...")
    fcst = sf.forecast(df=df, h=HORIZON, level=[90])
    parts = []
    for name in names:
        sub = fcst[["unique_id", "ds", name, f"{name}-lo-90", f"{name}-hi-90"]].copy()
        sub.columns = ["region", "forecast_date", "predicted_demand_mw", "lo_90", "hi_90"]
        sub["model"] = name
        parts.append(sub)
    forecast = pd.concat(parts, ignore_index=True)
    forecast["generated_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)

    # --- write back to DuckDB --------------------------------------------
    con.execute("CREATE SCHEMA IF NOT EXISTS forecast;")
    con.register("acc_df", accuracy)
    con.register("fc_df", forecast)
    con.execute("CREATE OR REPLACE TABLE forecast.forecast_accuracy AS SELECT * FROM acc_df;")
    con.execute("CREATE OR REPLACE TABLE forecast.demand_forecast AS SELECT * FROM fc_df;")

    # --- proof -----------------------------------------------------------
    print("\nBacktest MAPE % by region x model (lower is better):")
    print(accuracy.pivot(index="region", columns="model", values="mape").to_string())
    best = (
        accuracy.loc[accuracy.groupby("region")["mape"].idxmin()][["region", "model", "mape"]]
        .reset_index(drop=True)
    )
    print("\nBest model per region:")
    print(best.to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
