select b.region, r.region_name, b.engine, b.model, b.mae, b.rmse, b.mape
from marts.fct_engine_benchmark b
join marts.dim_region r on b.region = r.region_id