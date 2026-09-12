---
title: Carbon intensity
---

How much carbon comes with each unit of power depends almost entirely on what is
burning in that state. These figures apply standard emission factors to each
fuel, so they are an **estimate** — good for comparing states and watching the
trend, not for reporting to a regulator.

```sql ci_trend
select region_name,
       date_trunc('month', settlement_day) as month,
       1000.0 * sum(est_emissions_tco2) / sum(total_generation_mwh) as carbon_intensity
from energy_grid.region_energy_daily
group by 1, 2
order by 2
```

<LineChart data={ci_trend} x=month y=carbon_intensity series=region_name yAxisTitle="kg CO₂/MWh" title="Estimated carbon intensity by state, monthly"/>

**Victoria is the dirtiest grid in the country** and it is not close — brown
coal emits about a third more carbon than black coal per unit of power, and
Victoria runs on brown coal. New South Wales and Queensland sit together below
it on black coal. South Australia, on wind, is a fraction of any of them. And
Tasmania, on hydro, is effectively zero.

## The last 30 days

```sql ci_latest
select region_name,
       1000.0 * sum(est_emissions_tco2) / sum(total_generation_mwh) as carbon_intensity
from energy_grid.region_energy_daily
where settlement_day >= (select max(settlement_day) - interval '30 days' from energy_grid.region_energy_daily)
group by 1
order by carbon_intensity desc
```

<BarChart data={ci_latest} x=region_name y=carbon_intensity swapXY=true yAxisTitle="kg CO₂/MWh" title="Estimated carbon intensity by state, last 30 days"/>

The practical point: the same kettle boiled in Hobart and in Melbourne has a
carbon footprint that differs by more than ten times, and nothing about the
kettle changed.
