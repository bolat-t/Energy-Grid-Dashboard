---
title: Demand forecast
---

How much power will each state need next week? It sounds like it should be easy
— demand has a strong weekly rhythm (quieter on weekends) and a strong yearly
one (summer and winter peaks) — and it mostly is, which is what makes it a good
test of whether a model is actually doing anything.

Pick a state. The solid line is what happened over the last two months; the
lighter one is the model's guess for the coming week.

```sql regions
select distinct region_name from energy_grid.region_daily order by 1
```

<Dropdown data={regions} name=region value=region_name defaultValue="New South Wales"/>

```sql actual_vs_fc
with actual as (
  select region_name, settlement_day as date, avg_demand_mw as demand, 'actual' as series
  from energy_grid.region_daily
  where interval_count >= 40
    and settlement_day >= (select max(settlement_day) - interval '60 days' from energy_grid.region_daily)
),
fc as (
  select region_name, forecast_date as date, predicted_demand_mw as demand, 'forecast' as series
  from energy_grid.demand_forecast
  where model = 'AutoETS'
)
select date, demand, series from actual where region_name = '${inputs.region.value}'
union all
select date, demand, series from fc where region_name = '${inputs.region.value}'
order by date
```

<LineChart data={actual_vs_fc} x=date y=demand series=series yAxisTitle="MW" title="Daily demand: the last 60 days, and the next 7"/>

## The next seven days

The forecast, with the range the model is 90% confident the real number will
land inside. The range widens the further out you look, which is the model
being honest about how little it knows about next Sunday.

```sql fc_table
select forecast_date, predicted_demand_mw, lo_90, hi_90
from energy_grid.demand_forecast
where model = 'AutoETS' and region_name = '${inputs.region.value}'
order by forecast_date
```

<DataTable data={fc_table}>
  <Column id=forecast_date title="Date"/>
  <Column id=predicted_demand_mw title="Forecast (MW)" fmt=num0/>
  <Column id=lo_90 title="Low (90%)" fmt=num0/>
  <Column id=hi_90 title="High (90%)" fmt=num0/>
</DataTable>

## How good is it, honestly

A forecast you cannot score is just a guess with a chart. So I tested it the
hard way: six separate times, I hid a week of real history from the model, asked
it to predict that week, and then measured how far off it was, as a percentage.
That percentage is the bar height below — **lower is better**. A score of 3
means the model was typically within about 3% of the truth.

The dark bar is the dumb baseline: *assume next week looks like last week*.
Any model worth keeping has to beat it. Both of mine do, in every state.

```sql acc
select region_name, model, mape
from energy_grid.forecast_accuracy
order by region_name, mape
```

<BarChart data={acc} x=region_name y=mape series=model type=grouped yAxisTitle="average error, %" title="Forecast error by state, over six hidden weeks"/>

The big, steady states — New South Wales and Queensland — forecast well, within
about 3%. South Australia is the hardest at around 7%, because a grid that runs
on weather is harder to predict than one that runs on coal. That is not a
modelling failure; it is the transition showing up in a new place.
