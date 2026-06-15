with regions as (

    select * from {{ ref('seed_region') }}

)

select
    region_id,
    region_name,
    state,
    timezone
from regions
