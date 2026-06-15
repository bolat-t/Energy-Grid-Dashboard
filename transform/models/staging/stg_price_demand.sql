with source as (

    select * from {{ source('aemo', 'price_demand') }}

),

cleaned as (

    select
        region,
        settlement_date,
        total_demand_mw,
        rrp_aud_mwh,
        period_type,

        -- AEMO switched from 30-minute to 5-minute settlement on 2021-10-01.
        -- Flagging the native resolution lets downstream models roll the two
        -- eras up to a single, comparable grain honestly.
        case
            when settlement_date > timestamp '2021-10-01 00:00:00' then 5
            else 30
        end as resolution_min,

        source_month,
        source_file

    from source

)

select * from cleaned
