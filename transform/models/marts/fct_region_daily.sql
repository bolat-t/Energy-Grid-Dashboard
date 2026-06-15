-- Daily per-region rollup. Aggregating to a daily grain makes the 30-minute
-- (pre-Oct-2021) and 5-minute (post) eras directly comparable for trend
-- analysis, while fct_price_demand retains the native interval grain.
with f as (

    select * from {{ ref('fct_price_demand') }}

)

select
    region,
    settlement_day,
    count(*) as interval_count,

    -- price (A$/MWh)
    round(avg(rrp_aud_mwh), 2) as avg_rrp,
    round(min(rrp_aud_mwh), 2) as min_rrp,
    round(max(rrp_aud_mwh), 2) as max_rrp,
    round(median(rrp_aud_mwh), 2) as median_rrp,
    sum(case when is_negative_price then 1 else 0 end) as negative_price_intervals,
    round(
        100.0 * sum(case when is_negative_price then 1 else 0 end) / count(*), 2
    ) as negative_price_pct,

    -- demand (MW)
    round(avg(total_demand_mw), 1) as avg_demand_mw,
    round(max(total_demand_mw), 1) as peak_demand_mw,
    round(min(total_demand_mw), 1) as min_demand_mw

from f
group by region, settlement_day
