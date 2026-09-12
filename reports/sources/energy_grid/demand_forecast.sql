select
    f.region,
    r.region_name,
    f.model,
    f.forecast_date,
    f.predicted_demand_mw,
    f.lo_90,
    f.hi_90
from marts.fct_demand_forecast f
join marts.dim_region r on f.region = r.region_id