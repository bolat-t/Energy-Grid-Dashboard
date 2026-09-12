---
title: Renewables
---

The national number hides how uneven the transition is. Five states share one
market, and they are having five different experiences of it.

```sql ren_by_region
select region_name,
       date_trunc('month', settlement_day) as month,
       sum(renewable_mwh) / sum(total_generation_mwh) as renewable_share_pct
from energy_grid.region_energy_daily
group by 1, 2
order by 2
```

<LineChart data={ren_by_region} x=month y=renewable_share_pct series=region_name yAxisTitle="% renewable" title="Renewable share by state, monthly"/>

Tasmania sits near 100% because it has always run on hydro; that is geography,
not policy. South Australia is the real story — a state that has rebuilt itself
around wind and solar and now runs on them roughly three-quarters of the time.
The three big coal states are bunched together at a third, and of those,
**Queensland is moving fastest**, on the back of utility-scale solar.

## The mix, month by month

Fossil generation has not collapsed. It has flattened, while the renewable band
underneath it widens. That is what a transition looks like in the middle rather
than at the end.

```sql mix_over_time
select date_trunc('month', settlement_day) as month,
       fuel_group,
       sum(generation_mwh) / 1000.0 as gwh
from energy_grid.generation_daily
group by 1, 2
order by 1
```

<AreaChart data={mix_over_time} x=month y=gwh series=fuel_group yAxisTitle="GWh / month" title="Generation by fuel group, monthly"/>

## What each state actually burns

The last 90 days, as a share of each state's own generation. Read it as a
fingerprint: Victoria is brown coal, New South Wales and Queensland are black
coal, South Australia is wind, Tasmania is water. Almost everything on the other
pages follows from this one chart.

```sql mix_by_region
select region_name,
       fueltech_label,
       sum(generation_mwh) / 1000.0 as gwh
from energy_grid.generation_daily
where settlement_day >= (select max(settlement_day) - interval '90 days' from energy_grid.generation_daily)
group by 1, 2
```

<BarChart data={mix_by_region} x=region_name y=gwh series=fueltech_label type=stacked100 title="Fuel mix by state, last 90 days"/>

A reminder on what is missing: rooftop solar. Australia has more of it per
person than anywhere on earth, and none of it appears here, because the market
sees it as demand that never showed up rather than as generation.
