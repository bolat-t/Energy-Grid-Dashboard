---
title: Renewables
---

Utility-scale renewable share by region, and the changing generation mix.
Excludes behind-the-meter rooftop solar (which AEMO treats as reduced demand).

```sql ren_by_region
select region_name,
       date_trunc('month', settlement_day) as month,
       sum(renewable_mwh) / sum(total_generation_mwh) as renewable_share_pct
from gridlens.region_energy_daily
group by 1, 2
order by 2
```

<LineChart data={ren_by_region} x=month y=renewable_share_pct series=region_name yAxisTitle="% renewable" title="Renewable share by region (monthly)"/>

South Australia (wind + solar) and Tasmania (hydro) lead; **Queensland is rising
fastest** as utility solar scales.

## Generation mix over time

```sql mix_over_time
select date_trunc('month', settlement_day) as month,
       fuel_group,
       sum(generation_mwh) / 1000.0 as gwh
from gridlens.generation_daily
group by 1, 2
order by 1
```

<AreaChart data={mix_over_time} x=month y=gwh series=fuel_group yAxisTitle="GWh / month" title="NEM generation by fuel group"/>

## Fuel mix by region (last 90 days)

```sql mix_by_region
select region_name,
       fueltech_label,
       sum(generation_mwh) / 1000.0 as gwh
from gridlens.generation_daily
where settlement_day >= (select max(settlement_day) - interval '90 days' from gridlens.generation_daily)
group by 1, 2
```

<BarChart data={mix_by_region} x=region_name y=gwh series=fueltech_label type=stacked100 title="Fuel mix share by region (last 90 days)"/>
