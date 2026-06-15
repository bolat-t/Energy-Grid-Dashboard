-- Daily generation energy by region x fuel-tech (GWh-scale story grain).
with g as (

    select * from {{ ref('fct_generation') }}

)

select
    region,
    fueltech,
    cast(interval_start as date) as settlement_day,
    sum(generation_mwh) as generation_mwh
from g
group by 1, 2, 3
