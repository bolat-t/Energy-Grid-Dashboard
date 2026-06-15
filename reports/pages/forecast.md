---
title: Demand forecast
---

7-day-ahead daily demand forecast (`statsforecast`). Models are backtested with a
rolling origin against a seasonal-naive baseline.

```sql regions
select distinct region_name from gridlens.region_daily order by 1
```

<Dropdown data={regions} name=region value=region_name defaultValue="New South Wales"/>

```sql actual_vs_fc
with actual as (
  select region_name, settlement_day as date, avg_demand_mw as demand, 'actual' as series
  from gridlens.region_daily
  where interval_count >= 40
    and settlement_day >= (select max(settlement_day) - interval '60 days' from gridlens.region_daily)
),
fc as (
  select region_name, forecast_date as date, predicted_demand_mw as demand, 'forecast (AutoETS)' as series
  from gridlens.demand_forecast
  where model = 'AutoETS'
)
select date, demand, series from actual where region_name = '${inputs.region.value}'
union all
select date, demand, series from fc where region_name = '${inputs.region.value}'
order by date
```

<LineChart data={actual_vs_fc} x=date y=demand series=series yAxisTitle="MW" title="Daily demand — last 60 days + 7-day forecast"/>

## Next 7 days

```sql fc_table
select forecast_date, predicted_demand_mw, lo_90, hi_90
from gridlens.demand_forecast
where model = 'AutoETS' and region_name = '${inputs.region.value}'
order by forecast_date
```

<DataTable data={fc_table}>
  <Column id=forecast_date title="Date"/>
  <Column id=predicted_demand_mw title="Forecast (MW)" fmt=num0/>
  <Column id=lo_90 title="Low (90%)" fmt=num0/>
  <Column id=hi_90 title="High (90%)" fmt=num0/>
</DataTable>

## Model accuracy

Backtest MAPE (%, lower is better). Both **AutoETS** and **MSTL** beat the
seasonal-naive baseline in every region.

```sql acc
select region_name, model, mape
from gridlens.forecast_accuracy
order by region_name, mape
```

<BarChart data={acc} x=region_name y=mape series=model type=grouped yAxisTitle="MAPE %" title="Backtest error by model & region"/>
