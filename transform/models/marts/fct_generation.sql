-- Generation by region x fuel-tech x 30-minute interval.
-- Per-DUID 5-minute SCADA (each reading = MW) is converted to energy
-- (MWh = MW x 5/60) and summed. Only positive output counts as generation, so
-- battery/pumped-hydro *charging* (negative SCADA) is excluded here.
with scada as (

    select * from {{ ref('stg_dispatch_scada') }}

),

duid as (

    select * from {{ ref('dim_duid') }}

)

select
    d.region,
    d.fueltech,
    time_bucket(interval '30 minutes', s.settlement_date) as interval_start,
    sum(greatest(s.scada_mw, 0)) * (5.0 / 60.0) as generation_mwh,
    sum(greatest(s.scada_mw, 0)) * (5.0 / 60.0) * 2.0 as generation_avg_mw
from scada s
inner join duid d on s.duid = d.duid
group by 1, 2, 3
