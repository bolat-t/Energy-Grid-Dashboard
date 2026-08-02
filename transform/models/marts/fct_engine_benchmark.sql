-- Warehouse-engine benchmark: Snowflake ML vs Python statsforecast, trained on
-- identical history and scored on the same held-out 7 days.
--
-- Sourced from a committed seed rather than a live table: this is a one-off
-- experiment run against Snowflake's 30-day trial, so the result is preserved
-- as data and stays reproducible after the trial lapses.
with b as (

    select * from {{ ref('seed_engine_benchmark') }}

)

select
    region,
    engine,
    model,
    cast(mae as double) as mae,
    cast(rmse as double) as rmse,
    cast(mape as double) as mape,
    cast(holdout_start as date) as holdout_start,
    cast(holdout_end as date) as holdout_end
from b
