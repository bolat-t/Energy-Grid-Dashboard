"""One-command Snowflake setup for the optional "credibility run" (SNOWFLAKE.md).

Creates the warehouse / database / schema (plus a credit resource monitor as a
spend guard), then loads raw price & demand from the Parquet export so
`dbt build --target snowflake` has a source to build on.

Idempotent: safe to re-run. Reads credentials from .env (gitignored) — nothing
is hard-coded and nothing is printed back except the account/user being used.

Run:
    uv run python -m gridlens.export_marts        # ensure the Parquet exists
    uv run python -m gridlens.setup_snowflake
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

from gridlens import config

EXPORT = config.DATA_DIR / "exports" / "raw_price_demand.parquet"

REQUIRED = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (avoids adding a dependency for one file)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_dotenv(config.PROJECT_ROOT / ".env")

    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        sys.exit(
            "Missing credentials in .env: "
            + ", ".join(missing)
            + "\nFill them in (see .env.example / SNOWFLAKE.md), then re-run."
        )

    account = os.environ["SNOWFLAKE_ACCOUNT"]
    user = os.environ["SNOWFLAKE_USER"]
    role = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "GRIDLENS_WH")
    database = os.environ.get("SNOWFLAKE_DATABASE", "GRIDLENS")

    if not EXPORT.exists():
        sys.exit(f"Missing {EXPORT}. Run: uv run python -m gridlens.export_marts")

    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas

    print(f"connecting to {account} as {user} (role {role})...")
    con = snowflake.connector.connect(
        account=account,
        user=user,
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=role,
        client_session_keep_alive=True,
    )
    cur = con.cursor()
    try:
        # --- spend guard first, so the warehouse is monitored from the start ---
        print("creating resource monitor (50 credits/month, suspend at 90%)...")
        try:
            cur.execute(
                """
                create resource monitor if not exists gridlens_rm
                  with credit_quota = 50 frequency = monthly
                  start_timestamp = immediately
                  triggers on 90 percent do suspend
                """
            )
        except Exception as exc:  # noqa: BLE001 - non-fatal; needs ACCOUNTADMIN
            print(f"  ! skipped resource monitor ({exc}); continuing without spend cap")

        print(f"creating warehouse {warehouse} (XSMALL, auto-suspend 60s)...")
        cur.execute(
            f"""
            create warehouse if not exists {warehouse}
              warehouse_size = xsmall auto_suspend = 60 auto_resume = true
              initially_suspended = true
            """
        )
        try:
            cur.execute(f"alter warehouse {warehouse} set resource_monitor = gridlens_rm")
        except Exception:  # noqa: BLE001 - monitor may not exist; harmless
            pass

        print(f"creating database {database} and schemas...")
        cur.execute(f"create database if not exists {database}")
        cur.execute(f"create schema if not exists {database}.raw")
        cur.execute(f"use warehouse {warehouse}")
        cur.execute(f"use database {database}")
        cur.execute("use schema raw")

        cur.execute(
            """
            create or replace table price_demand (
                region varchar,
                settlement_date timestamp_ntz,
                total_demand_mw double,
                rrp_aud_mwh double,
                period_type varchar,
                source_month varchar,
                source_file varchar
            )
            """
        )

        print(f"reading {EXPORT.name}...")
        ddb = duckdb.connect()
        df = ddb.execute(
            f"""
            select region, settlement_date, total_demand_mw, rrp_aud_mwh,
                   period_type, source_month, source_file
            from read_parquet('{EXPORT}')
            """
        ).df()
        ddb.close()
        df.columns = [c.upper() for c in df.columns]

        print(f"loading {len(df):,} rows into {database}.RAW.PRICE_DEMAND...")
        ok, nchunks, nrows, _ = write_pandas(
            con, df, "PRICE_DEMAND", schema="RAW", database=database,
            quote_identifiers=False, chunk_size=250_000,
        )
        if not ok:
            sys.exit("load failed")
        print(f"  loaded {nrows:,} rows in {nchunks} chunks")

        cur.execute("select count(*), min(settlement_date), max(settlement_date) from price_demand")
        n, mn, mx = cur.fetchone()
        print(f"\nverified in Snowflake: {n:,} rows | {mn} -> {mx}")
        print(
            "\nNext:\n"
            "  set -a && source .env && set +a\n"
            "  uv run dbt build --project-dir transform --profiles-dir transform "
            "--target snowflake \\\n"
            "    --select seed_region dim_region stg_price_demand fct_price_demand fct_region_daily\n"
            f"\nWhen finished:  alter warehouse {warehouse} suspend;"
        )
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    main()
