---
title: Energy Grid Dashboard — Australia's NEM at a glance
---

How renewables are reshaping price, demand, and carbon intensity across the five
National Electricity Market regions. Source: **AEMO** (public). Generation is
**utility-scale** (excludes rooftop PV); carbon intensity is **estimated** from
per-fuel emission factors.

```sql nem_latest
with monthly as (
  select date_trunc('month', settlement_day) as month,
         sum(renewable_mwh) as ren,
         sum(total_generation_mwh) as tot,
         sum(est_emissions_tco2) as emis
  from gridlens.region_energy_daily
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
from gridlens.region_daily
where settlement_day >= (select max(settlement_day) - interval '30 days' from gridlens.region_daily)
```

<BigValue data={nem_latest} value=renewable_share_pct fmt='pct1' title="Renewable share (utility-scale)"/>
<BigValue data={nem_latest} value=carbon_intensity fmt='num0' title="Carbon intensity (kg CO₂/MWh, est.)"/>
<BigValue data={price_latest} value=avg_price fmt='usd0' title="Avg wholesale price (30d)"/>
<BigValue data={price_latest} value=avg_demand fmt='num0' title="Avg demand MW (30d)"/>

## Renewable share is climbing

```sql nem_ren_trend
select date_trunc('month', settlement_day) as month,
       sum(renewable_mwh) / sum(total_generation_mwh) as renewable_share_pct
from gridlens.region_energy_daily
group by 1
order by 1
```

<LineChart data={nem_ren_trend} x=month y=renewable_share_pct yAxisTitle="% renewable" title="NEM utility-scale renewable share (monthly)"/>

## Where the power comes from

```sql fuel_mix_recent
select fuel_group,
       sum(generation_mwh) / 1000.0 as gwh
from gridlens.generation_daily
where settlement_day >= (select max(settlement_day) - interval '30 days' from gridlens.generation_daily)
group by 1
order by gwh desc
```

<BarChart data={fuel_mix_recent} x=fuel_group y=gwh swapXY=true yAxisTitle="GWh" title="Generation by fuel group, last 30 days"/>

## Explore

- [Renewables](/renewables) — share by region, changing fuel mix
- [Price & demand](/prices) — trends, the 2022 crisis, negative prices
- [Carbon intensity](/carbon) — estimated emissions by region
- [Demand forecast](/forecast) — 7-day forecast + backtest accuracy
- [Warehouse ML](/warehouse-ml) — Snowflake ML vs Python, and price anomaly detection

## How it's built

AEMO public data → Python ingest (`uv`) → **DuckDB** → **dbt** (3 dimensions, 9 facts,
68 tests) → **statsforecast** → this **Evidence.dev** site, rebuilt daily by a GitHub
Actions cron.
The same dbt project also builds on **Snowflake**, verified to produce identical marts.

<LinkButton url="/dbt/index.html">Browse the dbt docs & lineage graph →</LinkButton>
