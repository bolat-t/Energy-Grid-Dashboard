with source as (

    select * from {{ source('aemo', 'dispatch_unit_scada') }}

)

select
    settlement_date,
    duid,
    scada_mw,
    source_month
from source
where scada_mw is not null
  -- Each MMS monthly file ends with the following month's 00:00 reading. Drop
  -- that single spillover interval so monthly energy sums aren't a partial month.
  and settlement_date < date_trunc('month', (select max(settlement_date) from source))
