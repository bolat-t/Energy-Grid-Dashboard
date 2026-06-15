---
title: Carbon intensity
---

Estimated grid carbon intensity (kg CO₂-e per MWh), from per-fuel emission factors
applied to utility-scale generation. **Indicative** — not AEMO's official figures.

```sql ci_trend
select region_name,
       date_trunc('month', settlement_day) as month,
       1000.0 * sum(est_emissions_tco2) / sum(total_generation_mwh) as carbon_intensity
from gridlens.region_energy_daily
group by 1, 2
order by 2
```

<LineChart data={ci_trend} x=month y=carbon_intensity series=region_name yAxisTitle="kg CO₂/MWh" title="Estimated carbon intensity by region (monthly)"/>

Victoria's **brown coal** makes it the most carbon-intensive region; hydro-based
**Tasmania** is near zero.

## Latest snapshot

```sql ci_latest
select region_name,
       1000.0 * sum(est_emissions_tco2) / sum(total_generation_mwh) as carbon_intensity
from gridlens.region_energy_daily
where settlement_day >= (select max(settlement_day) - interval '30 days' from gridlens.region_energy_daily)
group by 1
order by carbon_intensity desc
```

<BarChart data={ci_latest} x=region_name y=carbon_intensity swapXY=true yAxisTitle="kg CO₂/MWh" title="Carbon intensity by region, last 30 days"/>
