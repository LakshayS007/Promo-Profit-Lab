-- Weekly spend and trips per household (all departments), for the campaign analysis.
with hh as (select distinct household_id from {{ ref('stg_transactions') }}),
weeks as (select range as week from range(1, 54)),
s as (
    select household_id, week, sum(net_sales) as net_sales, sum(shelf_value) as shelf_value,
           sum(retailer_discount) as retailer_discount, sum(manufacturer_coupon) as manufacturer_coupon,
           count(distinct basket_id) as trips
    from {{ ref('stg_transactions') }} group by 1, 2
)
select h.household_id, w.week, coalesce(net_sales,0) as net_sales, coalesce(shelf_value,0) as shelf_value,
       coalesce(retailer_discount,0) as retailer_discount, coalesce(manufacturer_coupon,0) as manufacturer_coupon,
       coalesce(trips,0) as trips
from hh h cross join weeks w left join s using (household_id, week)
