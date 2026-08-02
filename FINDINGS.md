# Energy Grid Dashboard — findings

What the model says about Australia's National Electricity Market. Coverage: price
& demand **Jun 2020 – May 2026** (30-min until Oct 2021, 5-min after); utility-scale
generation **Aug 2024 – Apr 2026**. Source: **AEMO** (public). Carbon intensity is
**estimated** from per-fuel emission factors. Every figure is reproducible from the
dbt marts.

## 1. Renewables are reshaping the grid
- Utility-scale renewable share (NEM) rose from **~34%** (late 2024) to **~36%** (early 2026);
  **Queensland climbed fastest, +7.7 pts**, as utility solar scaled.
- By region (2025): **Tasmania ~100%** (hydro), **South Australia ~72–76%** (wind + solar),
  Victoria / NSW / Queensland **~27–34%**.
- *Caveat:* excludes behind-the-meter rooftop PV, which is large in Australia and would push
  the totals higher — AEMO treats rooftop as reduced operational demand.

## 2. Negative prices — the clearest renewable signal
- **13.7%** of all 5-minute intervals across the NEM cleared **below $0/MWh** (2020–2026).
- Frequency climbed from **5.1% (2020) to 18.4% (2025)**. Part of the 2020→21 jump is the
  30→5-minute settlement change; the 2021→25 rise is like-for-like.
- 2025 by region: **SA 30%** of intervals, VIC 24%, QLD 20%, NSW 14%, **TAS 3%** — almost
  perfectly ordered by renewable penetration.

## 3. Carbon intensity follows the fuel
- Estimated NEM carbon intensity eased from **~607 to ~590 kg CO₂-e/MWh**.
- By region: **Victoria ~776** (brown coal — the most emissions-intensive fuel) >
  **NSW / QLD ~605** (black coal) > **SA ~115** > **Tasmania ~0** (hydro).

## 4. Price — the 2022 crisis and a volatile recovery
- Monthly average prices spiked to **~$400/MWh in mid-2022** (coal-unit outages + a global
  gas-price spike, which briefly triggered AEMO to suspend the spot market).
- The data spans the market's bounds: a **−$1,000 floor** and the indexed **market price cap**,
  which climbed **$10,034 (2020) → $20,300 (2025–26)**.

## 5. Demand is forecastable
- 7-day-ahead daily demand forecast (`statsforecast`): **MAPE 3–7%** (NSW/QLD ~3%, SA ~7%).
- **AutoETS** and **MSTL** beat a seasonal-naive baseline by **16–31%** in every region,
  capturing both weekly (weekday/weekend) and annual seasonality.

## Method & honesty notes
- **Utility-scale only:** generation is NEMWEB dispatch SCADA; it excludes rooftop PV.
- **Estimated carbon:** indicative per-fuel emission factors (`seed_fueltech.csv`), not
  unit-level AEMO figures — labelled as such throughout.
- Some trend windows aren't season-matched; the dashboard shows the full series so seasonality
  is visible rather than hidden.
- Data © AEMO, used for non-commercial, educational purposes.
