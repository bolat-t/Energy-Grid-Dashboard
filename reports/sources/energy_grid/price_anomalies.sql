select a.region, r.region_name, a.settlement_day, a.avg_rrp, a.expected_rrp,
       a.lower_bound, a.upper_bound, a.is_anomaly, a.distance, a.surprise_aud_mwh
from marts.fct_price_anomalies a
join marts.dim_region r on a.region = r.region_id