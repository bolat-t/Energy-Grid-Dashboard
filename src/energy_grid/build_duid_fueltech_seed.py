"""Build the DUID -> fuel-tech seed from AEMO's Registration & Exemption List.

Downloads the authoritative AEMO registration xlsx, reads the "PU and Scheduled
Loads" sheet, classifies each dispatchable unit (DUID) into a normalised
fuel-tech, and writes transform/seeds/seed_duid_fueltech.csv (joined to the
curated seed_fueltech reference downstream in dbt).

Run: uv run python -m energy_grid.build_duid_fueltech_seed
"""

from __future__ import annotations

import csv
import io
from collections import Counter

import httpx
from openpyxl import load_workbook

from energy_grid import config

REG_URL = (
    "https://www.aemo.com.au/-/media/files/electricity/nem/"
    "participant_information/nem-registration-and-exemption-list.xlsx"
)
SHEET = "PU and Scheduled Loads"
RAW_REG_DIR = config.RAW_DIR / "registration"
SEED_PATH = config.PROJECT_ROOT / "transform" / "seeds" / "seed_duid_fueltech.csv"
USER_AGENT = "Mozilla/5.0 (Energy Grid Dashboard analytics-engineering portfolio)"


def classify_fueltech(fuel_desc: str | None, tech_desc: str | None) -> str:
    """Map AEMO's fuel/technology descriptors to a normalised fuel-tech.

    Returns one of the keys present in seeds/seed_fueltech.csv so the downstream
    join keeps referential integrity.
    """
    f = (fuel_desc or "").lower()
    t = (tech_desc or "").lower()
    if "brown coal" in f:
        return "coal_brown"
    if "coal" in f:
        return "coal_black"
    if "battery" in f or "battery" in t:
        return "battery"
    if "water" in f or "hydro" in t:
        return "hydro"
    if "wind" in f or "wind" in t:
        return "wind"
    if "solar" in f or "photovoltaic" in t:
        return "solar"
    if any(k in f for k in ("biomass", "bagasse", "landfill", "waste", "biogas", "wood", "sewage")):
        return "bioenergy"
    if "gas" in f or "gas" in t or "fuel oil" in f:
        if "combined cycle" in t or "ccgt" in t:
            return "gas_ccgt"
        if "open cycle" in t or "ocgt" in t:
            return "gas_ocgt"
        if "steam" in t:
            return "gas_steam"
        if "reciprocating" in t or "recip" in t:
            return "gas_recip"
        return "gas_other"
    if any(k in f for k in ("diesel", "distillate", "oil", "kerosene")):
        return "distillate"
    return "other"


def fetch_registry() -> bytes:
    RAW_REG_DIR.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(
        REG_URL, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=90
    )
    resp.raise_for_status()
    # Keep a dated cached copy for provenance.
    (RAW_REG_DIR / "nem-registration-and-exemption-list.xlsx").write_bytes(resp.content)
    return resp.content


def build() -> None:
    wb = load_workbook(io.BytesIO(fetch_registry()), read_only=True, data_only=True)
    rows = wb[SHEET].iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(rows)]
    idx = {name: i for i, name in enumerate(header)}

    def col(row: tuple, name: str):
        i = idx.get(name)
        return row[i] if i is not None and i < len(row) else None

    seen: dict[str, dict] = {}
    for row in rows:
        duid = col(row, "DUID")
        if not duid or not str(duid).strip():
            continue
        duid = str(duid).strip()
        fuel_desc = col(row, "Fuel Source - Descriptor")
        tech_desc = col(row, "Technology Type - Descriptor")
        region = col(row, "Region")
        cap = col(row, "Reg Cap generation (MW)")
        seen[duid] = {
            "duid": duid,
            "station_name": (col(row, "Station Name") or "").strip(),
            "region": str(region).strip() if region else "",
            "dispatch_type": (col(row, "Dispatch Type") or "").strip(),
            "fuel_source": (fuel_desc or "").strip(),
            "technology": (tech_desc or "").strip(),
            "fueltech": classify_fueltech(fuel_desc, tech_desc),
            "reg_cap_mw": cap if cap is not None else "",
        }

    cols = [
        "duid", "station_name", "region", "dispatch_type",
        "fuel_source", "technology", "fueltech", "reg_cap_mw",
    ]
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SEED_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for duid in sorted(seen):
            writer.writerow(seen[duid])

    print(f"wrote {len(seen)} DUIDs -> {SEED_PATH.relative_to(config.PROJECT_ROOT)}")
    print("\nfuel-tech tally:")
    for ft, n in sorted(Counter(r["fueltech"] for r in seen.values()).items(), key=lambda x: -x[1]):
        print(f"  {ft:12} {n:4}")
    print("\nregion values:", sorted({r["region"] for r in seen.values()}))


if __name__ == "__main__":
    build()
