select e.*, r.region_name
from marts.fct_region_energy_daily e
join marts.dim_region r on e.region = r.region_id