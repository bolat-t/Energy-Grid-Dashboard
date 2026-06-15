select
    a.region,
    r.region_name,
    a.model,
    a.mae,
    a.rmse,
    a.mape
from marts.fct_forecast_accuracy a
join marts.dim_region r on a.region = r.region_id