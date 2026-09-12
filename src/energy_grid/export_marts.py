"""Export the marts the dashboard needs to portable Parquet.

This decouples Evidence.dev from the DuckDB storage format / connector version:
Evidence reads these Parquet files (version-independent) instead of opening the
warehouse file directly. Part of the pipeline: ... -> dbt build -> export_marts.

Run: uv run python -m energy_grid.export_marts
"""

from __future__ import annotations

import duckdb

from energy_grid import config

EXPORT_DIR = config.DATA_DIR / "exports"

QUERIES: dict[str, str] = {
    "region_daily": "select * from marts.fct_region_daily",
    "region_energy_daily": "select * from marts.fct_region_energy_daily",
    "generation_daily": """
        select g.region, r.region_name, g.settlement_day, g.fueltech,
               f.fueltech_label, f.fuel_group, f.is_renewable, g.generation_mwh
        from marts.fct_generation_daily g
        join marts.dim_fueltech f using (fueltech)
        join marts.dim_region r on g.region = r.region_id
    """,
    "demand_forecast": "select * from marts.fct_demand_forecast",
    "forecast_accuracy": "select * from marts.fct_forecast_accuracy",
    "dim_region": "select * from marts.dim_region",
    # raw price & demand too, for the optional Snowflake credibility run (SNOWFLAKE.md)
    "raw_price_demand": "select * from raw.price_demand",
}


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        for name, query in QUERIES.items():
            out = EXPORT_DIR / f"{name}.parquet"
            con.execute(f"COPY ({query}) TO '{out}' (FORMAT PARQUET)")
            n = con.execute(f"select count(*) from read_parquet('{out}')").fetchone()[0]
            print(f"  {name}.parquet: {n:,} rows")
    finally:
        con.close()
    print(f"exports written to {EXPORT_DIR.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
