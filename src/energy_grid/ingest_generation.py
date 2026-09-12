"""Ingest AEMO MMSDM DISPATCH_UNIT_SCADA (per-DUID 5-min generation) into DuckDB.

Source : AEMO NEMWEB MMSDM monthly archives (no API key). The files are in MMS
         CSV format (C/I/D row types); we keep the D (data) rows for UNIT_SCADA.
Output : raw.dispatch_unit_scada (settlement_date, duid, scada_mw, source_month).
Notes  : MMSDM lags ~1-2 months, so the most recent months 404 and are skipped.
         Monthly zips (~29 MB) are cached for provenance; the ~330 MB CSV inside
         each is extracted to a temp file, loaded, then deleted.

Run: uv run python -m energy_grid.ingest_generation
"""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

import duckdb
import httpx

from energy_grid import config

RAW_SCADA_DIR = config.RAW_DIR / "dispatch_unit_scada"
USER_AGENT = "Mozilla/5.0 (Energy Grid Dashboard analytics-engineering portfolio)"


SCADA_HREF_RE = re.compile(
    r'href="([^"]*DISPATCH_UNIT_SCADA[^"]*\.zip)"', re.IGNORECASE
)


def resolve_url(client: httpx.Client, yyyymm: str) -> str | None:
    """Find the month's DISPATCH_UNIT_SCADA zip by reading the directory listing.

    The filenames contain '#', which NEMWEB percent-encodes inconsistently across
    CDN edges ('%2523' in some regions, '%23' in others) — a constructed URL that
    works locally can 404 from CI. Taking the href from the listing sidesteps it.
    Returns None when the month isn't published yet.
    """
    listing = config.AEMO_SCADA_DIR_URL.format(year=yyyymm[:4], month=yyyymm[4:])
    try:
        resp = client.get(listing)
        if resp.status_code != 200:
            return None
    except httpx.HTTPError:
        return None
    match = SCADA_HREF_RE.search(resp.text)
    if not match:
        return None
    href = match.group(1)
    return href if href.startswith("http") else config.NEMWEB_BASE + href


def _zip_path(yyyymm: str) -> Path:
    return RAW_SCADA_DIR / f"DISPATCH_UNIT_SCADA_{yyyymm}.zip"


def generation_months() -> list[str]:
    """Months to pull, ending ~2 months back to respect the MMSDM publish lag."""
    t = date.today()
    y, m = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
    return config.recent_months(config.GENERATION_MONTHS, end=date(y, m, 15))


def download_month(client: httpx.Client, yyyymm: str) -> str:
    zp = _zip_path(yyyymm)
    if zp.exists() and zp.stat().st_size > 0:
        return "cached"
    url = resolve_url(client, yyyymm)
    if url is None:
        return "missing"
    try:
        resp = client.get(url)
        if resp.status_code == 404:
            return "missing"
        resp.raise_for_status()
    except httpx.HTTPError as exc:  # noqa: BLE001 - report and continue
        print(f"  ! {yyyymm}: {exc}", file=sys.stderr)
        return "failed"
    zp.write_bytes(resp.content)
    return "downloaded"


def load_month(con: duckdb.DuckDBPyConnection, yyyymm: str) -> None:
    """Extract the month's CSV and append its UNIT_SCADA data rows to DuckDB."""
    zp = _zip_path(yyyymm)
    with zipfile.ZipFile(zp) as zf:
        member = zf.namelist()[0]
        tmp = RAW_SCADA_DIR / f"_tmp_{yyyymm}.csv"
        with zf.open(member) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
    try:
        # MMS CSV: D rows for UNIT_SCADA are
        #   D,DISPATCH,UNIT_SCADA,1,SETTLEMENTDATE,DUID,SCADAVALUE,LASTCHANGED
        # Read every line as 10 padded varchar columns, then keep the D rows.
        con.execute(
            """
            INSERT INTO raw.dispatch_unit_scada
            SELECT
                strptime(col4, '%Y/%m/%d %H:%M:%S') AS settlement_date,
                col5                                AS duid,
                try_cast(col6 AS DOUBLE)            AS scada_mw,
                ?                                   AS source_month
            FROM read_csv(
                ?, auto_detect = false, delim = ',', quote = '"', escape = '"',
                header = false, null_padding = true, ignore_errors = true,
                strict_mode = false,
                columns = {
                    'col0':'VARCHAR','col1':'VARCHAR','col2':'VARCHAR','col3':'VARCHAR',
                    'col4':'VARCHAR','col5':'VARCHAR','col6':'VARCHAR','col7':'VARCHAR',
                    'col8':'VARCHAR','col9':'VARCHAR'
                }
            )
            WHERE col0 = 'D' AND col2 = 'UNIT_SCADA'
            """,
            [yyyymm, str(tmp)],
        )
    finally:
        tmp.unlink(missing_ok=True)


def summarize(con: duckdb.DuckDBPyConnection) -> None:
    total, duids, mn, mx = con.execute(
        """
        select count(*), count(distinct duid),
               min(settlement_date), max(settlement_date)
        from raw.dispatch_unit_scada
        """
    ).fetchone()
    print(f"\nraw.dispatch_unit_scada: {total:,} rows | {duids} DUIDs | {mn} -> {mx}")
    print("\ntop fuel-techs by total generation (GWh, via DUID seed join):")
    # seed not yet in DuckDB at ingest time; this join reads the CSV seed directly.
    seed = config.PROJECT_ROOT / "transform" / "seeds" / "seed_duid_fueltech.csv"
    if seed.exists():
        for r in con.execute(
            """
            select coalesce(s.fueltech, 'UNMAPPED') ft,
                   round(sum(g.scada_mw) * (5/60.0) / 1000.0, 1) gwh
            from raw.dispatch_unit_scada g
            left join read_csv(?, header=true) s on g.duid = s.duid
            where g.scada_mw > 0
            group by 1 order by gwh desc limit 8
            """,
            [str(seed)],
        ).fetchall():
            print(f"  {r[0]:12} {r[1]:>12,} GWh")


def main() -> None:
    months = generation_months()
    print("Energy Grid Dashboard ingest — AEMO DISPATCH_UNIT_SCADA (per-DUID 5-min generation)")
    print(f"  window : {months[0]}..{months[-1]} ({len(months)} months)")
    RAW_SCADA_DIR.mkdir(parents=True, exist_ok=True)

    stats = {"downloaded": 0, "cached": 0, "missing": 0, "failed": 0}
    with httpx.Client(
        timeout=120.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        for m in months:
            stats[download_month(client, m)] += 1
    print(f"  download: {stats['downloaded']} new, {stats['cached']} cached, "
          f"{stats['missing']} not-yet-published, {stats['failed']} failed")

    con = duckdb.connect(str(config.DUCKDB_PATH))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        con.execute(
            """
            CREATE OR REPLACE TABLE raw.dispatch_unit_scada (
                settlement_date TIMESTAMP, duid VARCHAR,
                scada_mw DOUBLE, source_month VARCHAR
            );
            """
        )
        for m in months:
            if not _zip_path(m).exists():
                continue
            load_month(con, m)
            n = con.execute(
                "select count(*) from raw.dispatch_unit_scada where source_month = ?",
                [m],
            ).fetchone()[0]
            print(f"  loaded {m}: {n:,} rows")
        summarize(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
