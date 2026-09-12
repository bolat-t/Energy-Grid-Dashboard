---
title: Price & demand
---

Wholesale power in Australia is bought and sold every five minutes, and the
price can swing from below zero to above $20,000 a megawatt-hour inside a single
day. Averaged by month it tells a calmer story, with one very loud exception.

```sql price_trend
select region_name,
       date_trunc('month', settlement_day) as month,
       avg(avg_rrp) as avg_rrp
from energy_grid.region_daily
group by 1, 2
order by 2
```

<LineChart data={price_trend} x=month y=avg_rrp series=region_name yAxisTitle="$/MWh" title="Average wholesale price by state, monthly"/>

The spike is **mid-2022**. A run of coal-plant breakdowns collided with a global
gas shortage, prices went so high that the market operator suspended the market
entirely for a fortnight, and every state got dragged up together. It is the
single biggest event in the data and it needed no highlighting.

## Demand is flat, and that is the interesting part

Six years of population and economic growth, and the amount of power drawn from
the grid has barely moved. The saw-tooth is summer air-conditioning and winter
heating. The reason the line is not rising is sitting on people's roofs.

```sql demand_trend
select region_name,
       date_trunc('month', settlement_day) as month,
       avg(avg_demand_mw) as avg_demand
from energy_grid.region_daily
group by 1, 2
order by 2
```

<LineChart data={demand_trend} x=month y=avg_demand series=region_name yAxisTitle="MW" title="Average operational demand by state, monthly"/>

## When the price goes below zero

This is the chart that convinced me the transition was real. On a sunny, windy
afternoon there is more renewable power than the grid can use, and because
that power costs nothing to make, the price falls through zero — generators end
up paying to stay on. Across six years, **about one interval in seven** cleared
below $0. In 2025, South Australia did it **30% of the time**; Tasmania, with
hydro it can throttle, just 3%.

```sql neg_price
select region_name,
       date_trunc('month', settlement_day) as month,
       avg(negative_price_pct) / 100.0 as negative_price_pct
from energy_grid.region_daily
group by 1, 2
order by 2
```

<LineChart data={neg_price} x=month y=negative_price_pct series=region_name yAxisTitle="% of intervals < $0" title="Share of intervals priced below $0, monthly"/>

The ordering of the states on this chart is the ordering of their renewable
share, almost exactly. Nobody planned that; it falls out of the physics.
