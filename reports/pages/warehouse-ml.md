---
title: Warehouse ML
---

Modern cloud databases can run forecasting and anomaly detection *inside the
database*, from plain SQL, with no model code at all. Snowflake is one of them.
I already had a forecasting model written in Python, so the obvious question
was: **is the built-in one any good, and would I trust it?**

I ran two experiments to find out. Both used the same data as the rest of this
site.

## Experiment 1 — can the database forecast as well as Python?

The setup is the fairest one I could think of. Both were given the same six
years of daily demand history for each state, the **final week was hidden from
both of them**, and both had to predict it. I then measured how far each guess
was from what really happened, as a percentage. Lower is better.

```sql bench
select region_name, model, engine, mape
from energy_grid.engine_benchmark
order by region_name, mape
```

<BarChart data={bench} x=region_name y=mape series=model type=grouped yAxisTitle="average error, %" title="How far off each model was, by state"/>

```sql bench_avg
select model, engine, round(avg(mape), 2) as avg_mape
from energy_grid.engine_benchmark
group by model, engine
order by avg_mape
```

<DataTable data={bench_avg}>
  <Column id=model title="Model"/>
  <Column id=engine title="Runs in"/>
  <Column id=avg_mape title="Average error %" fmt=num2 contentType=colorscale scaleColor=red/>
</DataTable>

**It was a split decision, which is the honest and interesting result.** Snowflake
came out ahead on average — about 3.3% error against 4.0% for the best Python
model — and it was much better in South Australia, where it roughly halved the
error. But Python still won the two biggest states, New South Wales and
Queensland. Everything beat the *assume-next-week-is-like-last-week* baseline
at the bottom of the table.

One caveat I would rather state than hide: this is a single hidden week, which
is 35 predictions. Enough to be interesting; not enough to call a winner. The
six-week test on the [forecast page](/forecast) is the more serious one.

## Experiment 2 — can the database spot a weird day on its own?

Anomaly detection is a fancier name for a simple idea: show a model years of
normal behaviour, then ask it to point at anything that does not fit. I trained
Snowflake's version on **2020 to 2024** daily prices for each state, then had
it score every day from 2025 onward.

It flagged **54 days out of 2,585** — about 2% — as not fitting the pattern.

```sql anom_by_region
select region_name, sum(case when is_anomaly then 1 else 0 end) as anomalies
from energy_grid.price_anomalies
group by region_name
order by anomalies desc
```

<BarChart data={anom_by_region} x=region_name y=anomalies swapXY=true yAxisTitle="days flagged" title="Unusual price days per state, 2025 onward"/>

South Australia and Victoria get the most flags, and they are the two states
most exposed to weather. New South Wales and Queensland, running steadily on
coal, barely register. That is the same ranking as the renewables page, arrived
at by a completely different route, which is reassuring.

```sql top_anom
select settlement_day, region_name, avg_rrp, expected_rrp, surprise_aud_mwh
from energy_grid.price_anomalies
where is_anomaly
order by distance desc
limit 10
```

<DataTable data={top_anom}>
  <Column id=settlement_day title="Date"/>
  <Column id=region_name title="State"/>
  <Column id=avg_rrp title="Actual $/MWh" fmt=usd0/>
  <Column id=expected_rrp title="Model expected" fmt=usd0/>
  <Column id=surprise_aud_mwh title="Surprise" fmt=usd0/>
</DataTable>

The test of an anomaly detector is whether the things it flags are real. These
were. On **26 January 2026** — a public holiday in a heatwave — South Australia
cleared **$2,457** against an expected $75. And on **12 and 26 June 2025** it
flagged Victoria, South Australia and Tasmania on the same evenings, without
being told they were connected. Those were cold-snap winter peaks that hit the
whole southern grid at once. It found the weather by looking at the prices.
