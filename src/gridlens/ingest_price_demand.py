"""Ingest AEMO aggregated price & demand (5-min) into the DuckDB raw layer.

Source : AEMO public "Aggregated price and demand" monthly CSVs (one per NEM
         region). No API key required. License: AEMO public data, attributed
         in the README.
Output : data/gridlens.duckdb -> schema ``raw`` -> table ``price_demand``.
         Downloaded CSVs are cached under data/raw/price_demand/ as the
         immutable landing copy (provenance).

Run:  uv run python -m gridlens.ingest_price_demand
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import httpx

from gridlens import config

RAW_PD_DIR = config.RAW_DIR / "price_demand"
# AEMO's web layer 403s some default clients; a browser-ish UA is reliable.
USER_AGENT = "Mozilla/5.0 (GridLens analytics-engineering portfolio)"


def _target_path(yyyymm: str, region: str) -> Path:
    return RAW_PD_DIR / f"PRICE_AND_DEMAND_{yyyymm}_{region}.csv"


def download_file(client: httpx.Client, yyyymm: str, region: str) -> str:
    """Download one month/region CSV unless already cached. Returns a status."""
    path = _target_path(yyyymm, region)
    if path.exists() and path.stat().st_size > 0:
        return "cached"
    url = config.AEMO_PRICE_DEMAND_URL.format(yyyymm=yyyymm, region=region)
    resp = client.get(url)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    return "downloaded"


def download_all(
    months: list[str], regions: list[str], *, workers: int = 5
) -> dict[str, int]:
    RAW_PD_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(m, r) for m in months for r in regions]
    stats = {"downloaded": 0, "cached": 0, "failed": 0}
    with httpx.Client(
        timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(download_file, client, m, r): (m, r) for m, r in jobs
            }
            for fut in as_completed(futures):
                m, r = futures[fut]
                try:
                    stats[fut.result()] += 1
                except Exception as exc:  # noqa: BLE001 - report and keep going
                    stats["failed"] += 1
                    print(f"  ! failed {m} {r}: {exc}", file=sys.stderr)
    return stats


def load_to_duckdb() -> None:
    """(Re)build raw.price_demand from every cached CSV via a single glob read."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    glob = str(RAW_PD_DIR / "PRICE_AND_DEMAND_*.csv")
    con = duckdb.connect(str(config.DUCKDB_PATH))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        con.execute(
            r"""
            CREATE OR REPLACE TABLE raw.price_demand AS
            SELECT
                REGION                                          AS region,
                strptime(SETTLEMENTDATE, '%Y/%m/%d %H:%M:%S')   AS settlement_date,
                TOTALDEMAND                                     AS total_demand_mw,
                RRP                                             AS rrp_aud_mwh,
                PERIODTYPE                                      AS period_type,
                regexp_extract(filename, 'PRICE_AND_DEMAND_(\d{6})_', 1)
                                                                AS source_month,
                filename                                        AS source_file
            FROM read_csv(
                ?,
                header = true,
                filename = true,
                columns = {
                    'REGION': 'VARCHAR',
                    'SETTLEMENTDATE': 'VARCHAR',
                    'TOTALDEMAND': 'DOUBLE',
                    'RRP': 'DOUBLE',
                    'PERIODTYPE': 'VARCHAR'
                }
            );
            """,
            [glob],
        )
    finally:
        con.close()


def summarize() -> None:
    """Print proof: totals, per-region coverage, and a small sample."""
    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        total = con.execute("SELECT count(*) FROM raw.price_demand").fetchone()[0]
        print(f"\nraw.price_demand: {total:,} rows")
        print("\nregion |      rows | first interval      -> last interval       | avg RRP | avg dmd")
        print("-" * 92)
        for r in con.execute(
            """
            SELECT region, count(*) AS n,
                   min(settlement_date) AS first_ts,
                   max(settlement_date) AS last_ts,
                   round(avg(rrp_aud_mwh), 2) AS avg_rrp,
                   round(avg(total_demand_mw)) AS avg_dmd
            FROM raw.price_demand
            GROUP BY region ORDER BY region
            """
        ).fetchall():
            print(
                f"{r[0]:6} | {r[1]:>9,} | {r[2]} -> {r[3]} | "
                f"${r[4]:>6} | {int(r[5]):>5} MW"
            )
        print("\nsample — NSW1, latest 3 intervals:")
        for r in con.execute(
            """
            SELECT settlement_date, total_demand_mw, rrp_aud_mwh
            FROM raw.price_demand WHERE region = 'NSW1'
            ORDER BY settlement_date DESC LIMIT 3
            """
        ).fetchall():
            print(f"  {r[0]} | {r[1]:>8.1f} MW | ${r[2]:.2f}/MWh")
    finally:
        con.close()


def main() -> None:
    months = config.recent_months(config.HISTORY_MONTHS)
    regions = config.NEM_REGIONS
    print("GridLens ingest — AEMO aggregated price & demand (5-min)")
    print(f"  window : {months[0]}..{months[-1]} ({len(months)} months)")
    print(f"  regions: {', '.join(regions)}")
    print(f"  files  : {len(months) * len(regions)}\n")

    stats = download_all(months, regions)
    print(
        f"\ndownload: {stats['downloaded']} new, "
        f"{stats['cached']} cached, {stats['failed']} failed"
    )
    if stats["failed"] and stats["downloaded"] == 0 and stats["cached"] == 0:
        sys.exit("No data downloaded — aborting before load.")

    load_to_duckdb()
    summarize()


if __name__ == "__main__":
    main()
