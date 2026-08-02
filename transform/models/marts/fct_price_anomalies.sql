-- Daily price scored against a per-region 2020-2024 baseline by
-- SNOWFLAKE.ML.ANOMALY_DETECTION. `is_anomaly` marks days outside the band.
--
-- Sourced from a committed seed (see fct_engine_benchmark for the rationale).
with a as (

    select * from {{ ref('seed_price_anomalies') }}

)

select
    region,
    cast(settlement_day as date) as settlement_day,
    cast(avg_rrp as double) as avg_rrp,
    cast(expected_rrp as double) as expected_rrp,
    cast(lower_bound as double) as lower_bound,
    cast(upper_bound as double) as upper_bound,
    cast(is_anomaly as boolean) as is_anomaly,
    cast(distance as double) as distance,
    cast(avg_rrp as double) - cast(expected_rrp as double) as surprise_aud_mwh
from a
