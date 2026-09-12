select
    g.region,
    r.region_name,
    g.settlement_day,
    g.fueltech,
    f.fueltech_label,
    f.fuel_group,
    f.is_renewable,
    g.generation_mwh
from marts.fct_generation_daily g
join marts.dim_fueltech f using (fueltech)
join marts.dim_region r on g.region = r.region_id