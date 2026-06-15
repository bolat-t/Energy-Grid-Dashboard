---
title: Price & demand
---

Wholesale price (Regional Reference Price) and operational demand across the NEM.

```sql price_trend
select region_name,
       date_trunc('month', settlement_day) as month,
       avg(avg_rrp) as avg_rrp
from gridlens.region_daily
group by 1, 2
order by 2
```

<LineChart data={price_trend} x=month y=avg_rrp series=region_name yAxisTitle="$/MWh" title="Average wholesale price by region (monthly)"/>

The **2022 energy crisis** (coal-unit outages + a global gas-price spike, which
briefly suspended the market) stands out clearly.

## Operational demand

```sql demand_trend
select region_name,
       date_trunc('month', settlement_day) as month,
       avg(avg_demand_mw) as avg_demand
from gridlens.region_daily
group by 1, 2
order by 2
```

<LineChart data={demand_trend} x=month y=avg_demand series=region_name yAxisTitle="MW" title="Average operational demand by region (monthly)"/>

## The rise of negative prices

When renewables flood the grid, wholesale prices fall below zero. The share of
intervals priced under **$0/MWh** has climbed sharply — led by South Australia.

```sql neg_price
select region_name,
       date_trunc('month', settlement_day) as month,
       avg(negative_price_pct) / 100.0 as negative_price_pct
from gridlens.region_daily
group by 1, 2
order by 2
```

<LineChart data={neg_price} x=month y=negative_price_pct series=region_name yAxisTitle="% of intervals < $0" title="Negative-price frequency (monthly)"/>
