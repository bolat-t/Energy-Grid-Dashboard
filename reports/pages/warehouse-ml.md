---
title: Warehouse ML
---

The same modelled data, run through **Snowflake's in-database ML** — then compared
honestly against the Python models. Two questions: *can the warehouse forecast as well
as Python?* and *can it spot unusual market days on its own?*

## 1. Snowflake ML vs Python — same split, same actuals

Both engines trained on identical history (2020-06-01 → 2026-05-24) and predicted the
**same held-out 7 days**, scored against the same actuals. Lower MAPE is better.

```sql bench
select region_name, model, engine, mape
from gridlens.engine_benchmark
order by region_name, mape
```

<BarChart data={bench} x=region_name y=mape series=model type=grouped yAxisTitle="MAPE %" title="Held-out forecast error by engine & region"/>

```sql bench_avg
select model, engine, round(avg(mape), 2) as avg_mape
from gridlens.engine_benchmark
group by model, engine
order by avg_mape
```

<DataTable data={bench_avg}>
  <Column id=model title="Model"/>
  <Column id=engine title="Engine"/>
  <Column id=avg_mape title="Avg MAPE %" fmt=num2 contentType=colorscale scaleColor=red/>
</DataTable>

**The result is a split decision, which is the interesting part.** Snowflake ML has the
better average (3.34% vs AutoETS 4.01%) and is markedly stronger on the small, volatile
regions — in South Australia it more than halves the error. Python's AutoETS still wins the
two big stable series, NSW and Queensland. Every model beats the seasonal-naive baseline.

> Caveat, stated plainly: this is a **single 7-day holdout (35 predictions)** — enough to be
> suggestive, not enough to be conclusive. The rolling-origin backtest on the
> [forecast page](/forecast) is the more rigorous test of the Python models.

## 2. Anomaly detection — unusual price days

`SNOWFLAKE.ML.ANOMALY_DETECTION` learned a per-region price baseline from 2020-2024, then
scored every day from 2025 on. It flagged **54 of 2,585 region-days (2.1%)**.

```sql anom_by_region
select region_name, sum(case when is_anomaly then 1 else 0 end) as anomalies
from gridlens.price_anomalies
group by region_name
order by anomalies desc
```

<BarChart data={anom_by_region} x=region_name y=anomalies swapXY=true yAxisTitle="flagged days" title="Anomalous price days by region (2025+)"/>

The ranking mirrors the renewables story: **South Australia and Victoria** — the most
weather-exposed grids — throw the most surprises, while NSW and Queensland are stable.

```sql top_anom
select settlement_day, region_name, avg_rrp, expected_rrp, surprise_aud_mwh
from gridlens.price_anomalies
where is_anomaly
order by distance desc
limit 10
```

<DataTable data={top_anom}>
  <Column id=settlement_day title="Date"/>
  <Column id=region_name title="Region"/>
  <Column id=avg_rrp title="Actual $/MWh" fmt=usd0/>
  <Column id=expected_rrp title="Expected $/MWh" fmt=usd0/>
  <Column id=surprise_aud_mwh title="Surprise" fmt=usd0/>
</DataTable>

Two patterns stand out, and both are real market events rather than noise:

- **26 Jan 2026 — South Australia cleared $2,457/MWh against an expected $75.** A summer
  heatwave on a public holiday.
- **12 and 26 June 2025 flag in Victoria, South Australia *and* Tasmania at once** — the
  model independently rediscovered NEM-wide winter evening peaks, which is a good sign it's
  detecting market physics rather than per-series noise.
