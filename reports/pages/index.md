---
title: Energy Grid Dashboard
---

Australia's electricity market keeps a five-minute record of itself: what power
cost, how much was used, and which generators supplied it, for every region,
going back years. It is public and almost nobody reads it. This dashboard turns
six years of that record into one question — **what is the shift to renewables
actually doing to the grid?**

Everything here is AEMO's own data and it refreshes every morning. Two honest
caveats. Generation is utility-scale only: rooftop solar, which is enormous in
Australia, shows up as *less demand* rather than *more supply*, so it is not in
these figures. And carbon intensity is an estimate from standard emission factors
per fuel, not an official number.

```sql nem_latest
with monthly as (
  select date_trunc('month', settlement_day) as month,
         sum(renewable_mwh) as ren,
         sum(total_generation_mwh) as tot,
         sum(est_emissions_tco2) as emis
  from energy_grid.region_energy_daily
  group by 1
)
select month,
       ren / tot as renewable_share_pct,
       1000.0 * emis / tot as carbon_intensity
from monthly
order by month desc
limit 1
```

```sql price_latest
select avg(avg_rrp) as avg_price,
       avg(avg_demand_mw) as avg_demand
from energy_grid.region_daily
where settlement_day >= (select max(settlement_day) - interval '30 days' from energy_grid.region_daily)
```

<BigValue data={nem_latest} value=renewable_share_pct fmt='pct1' title="Renewable share (utility-scale)"/>
<BigValue data={nem_latest} value=carbon_intensity fmt='num0' title="Carbon intensity (kg CO₂/MWh, est.)"/>
<BigValue data={price_latest} value=avg_price fmt='usd0' title="Avg wholesale price (30d)"/>
<BigValue data={price_latest} value=avg_demand fmt='num0' title="Avg demand MW (30d)"/>

## Renewables are about a third of the grid, and climbing

The share of utility-scale generation coming from wind, solar and hydro. It
breathes with the seasons — solar peaks in summer and sags in winter — but the
trend underneath the wobble is up, and it has not gone backwards.

```sql nem_ren_trend
select date_trunc('month', settlement_day) as month,
       sum(renewable_mwh) / sum(total_generation_mwh) as renewable_share_pct
from energy_grid.region_energy_daily
group by 1
order by 1
```

<LineChart data={nem_ren_trend} x=month y=renewable_share_pct yAxisTitle="% renewable" title="Renewable share of utility-scale generation, monthly"/>

## What is actually generating, right now

The last 30 days by fuel. Coal is still the single biggest source of power in
the country. It just is not the growing one.

```sql fuel_mix_recent
select fuel_group,
       sum(generation_mwh) / 1000.0 as gwh
from energy_grid.generation_daily
where settlement_day >= (select max(settlement_day) - interval '30 days' from energy_grid.generation_daily)
group by 1
order by gwh desc
```

<BarChart data={fuel_mix_recent} x=fuel_group y=gwh swapXY=true yAxisTitle="GWh" title="Generation by fuel group, last 30 days"/>

## Read on

- [Renewables](/renewables) — where the shift is happening, state by state
- [Price & demand](/prices) — the 2022 crisis, and why prices keep dropping below zero
- [Carbon intensity](/carbon) — how the fuel mix decides each state's emissions
- [Demand forecast](/forecast) — next week, and an honest score for the model
- [Warehouse ML](/warehouse-ml) — what happened when I let the database do the forecasting

## How it is built

AEMO's public files are pulled every morning into a DuckDB warehouse, modelled with
dbt into tested tables, and rendered into this site by a GitHub Actions job. The
same dbt project also builds on Snowflake — I checked, and the numbers come out
identical. The full model lineage is documented below.

<LinkButton url="/dbt/index.html">Browse the data model and lineage →</LinkButton>
