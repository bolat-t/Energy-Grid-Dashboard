-- Dispatchable unit dimension: maps each DUID to its region and fuel-tech,
-- sourced from AEMO's Registration & Exemption List (see build_duid_fueltech_seed).
with d as (

    select * from {{ ref('seed_duid_fueltech') }}

)

select
    duid,
    station_name,
    region,
    dispatch_type,
    fueltech,
    try_cast(reg_cap_mw as double) as reg_cap_mw
from d
where region in ('NSW1', 'QLD1', 'VIC1', 'SA1', 'TAS1')
