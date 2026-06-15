-- Rolling-origin backtest accuracy per region per model (lower = better).
-- SeasonalNaive is the baseline the learned models are judged against.
with a as (

    select * from {{ source('forecast', 'forecast_accuracy') }}

)

select
    region,
    model,
    mae,
    rmse,
    mape,
    n_windows,
    horizon
from a
