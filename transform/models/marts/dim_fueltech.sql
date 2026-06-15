-- Fuel-tech reference: renewable flag and *estimated* emission factor per type.
-- Emission factors are indicative per-fuel values (t CO2-e / MWh sent out) used
-- for an estimated carbon intensity; they are not unit-specific AEMO figures.
with ft as (

    select * from {{ ref('seed_fueltech') }}

)

select
    fueltech,
    fueltech_label,
    fuel_group,
    cast(is_renewable as boolean) as is_renewable,
    cast(emission_factor_t_co2_per_mwh as double) as emission_factor_t_co2_per_mwh
from ft
