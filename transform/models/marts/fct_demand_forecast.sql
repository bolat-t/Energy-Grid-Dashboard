-- 7-day-ahead daily demand forecast per region per model, with 90% interval.
-- Produced by energy_grid.forecast_demand (statsforecast); served here for the dashboard.
with f as (

    select * from {{ source('forecast', 'demand_forecast') }}

)

select
    region,
    model,
    cast(forecast_date as date) as forecast_date,
    round(predicted_demand_mw, 1) as predicted_demand_mw,
    round(lo_90, 1) as lo_90,
    round(hi_90, 1) as hi_90,
    generated_at
from f
