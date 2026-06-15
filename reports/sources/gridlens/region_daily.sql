select rd.*, r.region_name
from marts.fct_region_daily rd
join marts.dim_region r on rd.region = r.region_id