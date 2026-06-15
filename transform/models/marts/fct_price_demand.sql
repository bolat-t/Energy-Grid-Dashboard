-- Atomic fact: one row per region per settlement interval (native grain).
with stg as (

    select * from {{ ref('stg_price_demand') }}

)

select
    {{ dbt_utils.generate_surrogate_key(['region', 'settlement_date']) }}
        as price_demand_id,
    region,
    settlement_date,
    cast(settlement_date as date) as settlement_day,
    rrp_aud_mwh,
    total_demand_mw,
    resolution_min,
    (rrp_aud_mwh < 0) as is_negative_price
from stg
