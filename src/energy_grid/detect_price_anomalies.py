"""Flag unusual wholesale-price days with SNOWFLAKE.ML.ANOMALY_DETECTION.

Trains a per-region baseline on 2020-2024 daily average price, then scores
2025-onward: days whose price falls outside the model's expected band are
flagged. Results land in DuckDB `forecast.price_anomalies` for dbt/the dashboard.

Run: uv run python -m energy_grid.detect_price_anomalies
"""

from __future__ import annotations

import os
import sys

import duckdb
import pandas as pd

from energy_grid import config
from energy_grid.setup_snowflake import load_dotenv

TRAIN_END = "2024-12-31"


def main() -> None:
    load_dotenv(config.PROJECT_ROOT / ".env")
    if not os.environ.get("SNOWFLAKE_ACCOUNT"):
        sys.exit("No Snowflake credentials in .env — see SNOWFLAKE.md")

    import snowflake.connector

    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "ENERGY_GRID_WH")
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=warehouse,
        database=os.environ.get("SNOWFLAKE_DATABASE", "ENERGY_GRID"),
        schema="MARTS",
    )
    cur = con.cursor()
    print("Price anomaly detection — SNOWFLAKE.ML.ANOMALY_DETECTION")
    try:
        for name, predicate in [
            ("ad_train", f"settlement_day <= date '{TRAIN_END}'"),
            ("ad_score", f"settlement_day >  date '{TRAIN_END}'"),
        ]:
            cur.execute(
                f"""
                create or replace view {name} as
                select region,
                       to_timestamp_ntz(settlement_day) as ts,
                       avg_rrp as y
                from energy_grid.marts.fct_region_daily
                where {predicate}
                """
            )
        cur.execute("select count(*) from ad_train")
        n_train = cur.fetchone()[0]
        cur.execute("select count(*) from ad_score")
        n_score = cur.fetchone()[0]
        print(f"  train: {n_train:,} region-days (to {TRAIN_END}) | score: {n_score:,}")

        print("  training baseline model...")
        cur.execute(
            """
            create or replace snowflake.ml.anomaly_detection price_ad(
                input_data => system$reference('view','ad_train'),
                series_colname => 'REGION',
                timestamp_colname => 'TS',
                target_colname => 'Y',
                label_colname => '')
            """
        )

        print("  scoring recent days...")
        cur.execute(
            """
            call price_ad!detect_anomalies(
                input_data => system$reference('view','ad_score'),
                series_colname => 'REGION',
                timestamp_colname => 'TS',
                target_colname => 'Y')
            """
        )
        rows = cur.fetchall()
        cols = [d[0].lower() for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)
    finally:
        for v in ("ad_train", "ad_score"):
            cur.execute(f"drop view if exists {v}")
        cur.execute(f"alter warehouse {warehouse} suspend")
        cur.close()
        con.close()

    df["region"] = df["series"].astype(str).str.strip('"')
    df["settlement_day"] = pd.to_datetime(df["ts"]).dt.normalize()
    out = df[["region", "settlement_day", "y", "forecast",
              "lower_bound", "upper_bound", "is_anomaly", "distance"]].copy()
    out = out.rename(columns={"y": "avg_rrp", "forecast": "expected_rrp"})
    for c in ["avg_rrp", "expected_rrp", "lower_bound", "upper_bound", "distance"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").round(2)
    out["is_anomaly"] = out["is_anomaly"].astype(bool)

    # Written as a dbt seed (not just a DuckDB table) so the result survives the
    # Snowflake trial and the CI rebuild, which recreates the warehouse from scratch.
    seed = config.PROJECT_ROOT / "transform" / "seeds" / "seed_price_anomalies.csv"
    out.to_csv(seed, index=False)
    print(f"wrote {seed.relative_to(config.PROJECT_ROOT)} ({len(out):,} rows)")

    n_anom = int(out["is_anomaly"].sum())
    print(f"\nscored {len(out):,} region-days | flagged {n_anom} anomalies "
          f"({100 * n_anom / len(out):.1f}%)")
    print("\nby region:")
    for region, g in out.groupby("region"):
        print(f"  {region:>5}: {int(g['is_anomaly'].sum()):>3} anomalous days")
    top = out[out["is_anomaly"]].nlargest(8, "distance")
    print("\nmost extreme flagged days:")
    for _, r in top.iterrows():
        print(f"  {r['settlement_day'].date()} {r['region']:>5} "
              f"actual ${r['avg_rrp']:>8.2f} vs expected ${r['expected_rrp']:>7.2f}")


if __name__ == "__main__":
    main()
