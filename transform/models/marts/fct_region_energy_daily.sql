-- Headline transition metrics per region per day:
--   * utility-scale renewable share (%)  -- excludes behind-the-meter rooftop PV
--   * estimated carbon intensity (kg CO2-e / MWh) from per-fuel emission factors
with gen as (

    select * from {{ ref('fct_generation_daily') }}

),

fueltech as (

    select * from {{ ref('dim_fueltech') }}

),

joined as (

    select
        gen.region,
        gen.settlement_day,
        gen.generation_mwh,
        fueltech.is_renewable,
        fueltech.emission_factor_t_co2_per_mwh
    from gen
    inner join fueltech on gen.fueltech = fueltech.fueltech

)

select
    region,
    settlement_day,
    round(sum(generation_mwh), 1) as total_generation_mwh,
    round(sum(case when is_renewable then generation_mwh else 0 end), 1) as renewable_mwh,
    round(
        100.0 * sum(case when is_renewable then generation_mwh else 0 end)
        / nullif(sum(generation_mwh), 0), 2
    ) as renewable_share_pct,
    round(sum(generation_mwh * emission_factor_t_co2_per_mwh), 1) as est_emissions_tco2,
    round(
        1000.0 * sum(generation_mwh * emission_factor_t_co2_per_mwh)
        / nullif(sum(generation_mwh), 0), 1
    ) as est_carbon_intensity_kg_per_mwh
from joined
group by 1, 2
