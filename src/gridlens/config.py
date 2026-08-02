"""Central configuration: paths, NEM regions, AEMO endpoints, ingest window.

AEMO public data requires no API key. Region/window settings live here so the
ingestion scripts and (later) the GitHub Actions cron share one source of truth.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    """Walk up from ``start`` to the first directory containing pyproject.toml.

    Works whether the package is imported from ``src/`` (editable) or from a
    ``.venv`` under the project root, so data paths resolve consistently.
    """
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return start.parent


# --- Paths ---------------------------------------------------------------
PROJECT_ROOT = _find_project_root(Path(__file__).resolve())
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DUCKDB_PATH = DATA_DIR / "gridlens.duckdb"

# --- NEM scope -----------------------------------------------------------
# National Electricity Market regions (excludes WA's WEM and the NT).
NEM_REGIONS: list[str] = ["NSW1", "QLD1", "VIC1", "SA1", "TAS1"]

# Human-readable region labels for the dashboard / marts.
REGION_LABELS: dict[str, str] = {
    "NSW1": "New South Wales",
    "QLD1": "Queensland",
    "VIC1": "Victoria",
    "SA1": "South Australia",
    "TAS1": "Tasmania",
}

# --- AEMO endpoints ------------------------------------------------------
# Aggregated price & demand: one CSV per region per month, 5-minute resolution.
# Columns: REGION, SETTLEMENTDATE, TOTALDEMAND, RRP, PERIODTYPE
AEMO_PRICE_DEMAND_URL = (
    "https://aemo.com.au/aemo/data/nem/priceanddemand/"
    "PRICE_AND_DEMAND_{yyyymm}_{region}.csv"
)

# Generation by unit: MMSDM monthly DISPATCH_UNIT_SCADA archive (per-DUID 5-min MW).
#
# These filenames contain literal '#' characters, and NEMWEB serves the encoding
# differently depending on which CDN edge answers: some regions publish (and only
# accept) '%2523' (double-encoded), others '%23'. Constructing the URL therefore
# works from one location and 404s from another. We scrape the month's directory
# listing and follow the href it gives us instead — correct from anywhere.
NEMWEB_BASE = "https://nemweb.com.au"
AEMO_SCADA_DIR_URL = (
    "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/{year}/"
    "MMSDM_{year}_{month}/MMSDM_Historical_Data_SQLLoader/DATA/"
)

# --- Ingest window -------------------------------------------------------
# How many complete calendar months of history to pull (env-overridable so the
# cron can pull a short window while a backfill can pull years).
HISTORY_MONTHS: int = int(os.environ.get("GRIDLENS_HISTORY_MONTHS", "72"))

# Generation history (heavier per-DUID SCADA) defaults shorter than price/demand.
GENERATION_MONTHS: int = int(os.environ.get("GRIDLENS_GENERATION_MONTHS", "24"))


def recent_months(n: int, *, end: date | None = None) -> list[str]:
    """Return the last ``n`` *complete* calendar months as ``YYYYMM``, ascending.

    "Complete" means strictly before the month of ``end`` (default: today), so we
    never request a partial, still-updating current month.
    """
    end = end or date.today()
    year, month = end.year, end.month
    out: list[str] = []
    for _ in range(n):
        month -= 1
        if month == 0:
            month, year = 12, year - 1
        out.append(f"{year}{month:02d}")
    return sorted(out)
