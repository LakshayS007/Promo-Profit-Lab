-- One row per in-scope product per week (weeks with no sales included): sales, discounts, display and mailer coverage,
-- and promotion type.
--
-- Everyday card pricing is NOT a promotion. Many products carry the same loyalty-card discount almost every week, so
-- each product's usual discount (median depth over the weeks it sold) is treated as part of its everyday price. Only a
-- discount deeper than usual counts as a price promotion, and only the part above usual counts as promotion spend.
with scope as (select product_id from {{ ref('dim_product') }} where in_scope),
weeks as (select range as week from range(1, 54)),
grid as (select product_id, week from scope cross join weeks),
sales as (
    select product_id, week, sum(quantity) as units, sum(shelf_value) as shelf_value, sum(net_sales) as net_sales,
           sum(retailer_discount) as retailer_discount, sum(manufacturer_coupon) as manufacturer_coupon,
           round(sum(retailer_discount) / nullif(sum(shelf_value), 0), 9) as discount_depth
    from {{ ref('stg_transactions') }} where product_id in (select product_id from scope) group by 1, 2
),
usual as (
    select product_id, median(discount_depth) as usual_depth from sales where shelf_value > 0 group by 1
),
-- weight each store by its share of the product's annual units, so promotion coverage reflects where it actually sells
store_w as (
    select product_id, store_id, sum(quantity) * 1.0 / sum(sum(quantity)) over (partition by product_id) as w
    from {{ ref('stg_transactions') }} where product_id in (select product_id from scope) group by 1, 2
),
promo as (
    select w.product_id, pr.week,
           -- rounded so the 50% thresholds below give the same answer however the parallel sum is ordered
           round(sum(case when pr.on_display then w.w else 0 end), 9) as display_share,
           round(sum(case when pr.in_mailer  then w.w else 0 end), 9) as feature_share
    from store_w w join {{ ref('stg_promotions') }} pr on pr.product_id = w.product_id and pr.store_id = w.store_id
    group by 1, 2
),
base as (
    select g.product_id, g.week,
           coalesce(s.units, 0) as units, coalesce(s.shelf_value, 0) as shelf_value, coalesce(s.net_sales, 0) as net_sales,
           coalesce(s.retailer_discount, 0) as retailer_discount, coalesce(s.manufacturer_coupon, 0) as manufacturer_coupon,
           s.discount_depth, coalesce(u.usual_depth, 0) as usual_depth,
           round(greatest(coalesce(s.discount_depth, 0) - coalesce(u.usual_depth, 0), 0), 9) as excess_depth,
           coalesce(p.display_share, 0) as display_share, coalesce(p.feature_share, 0) as feature_share
    from grid g left join sales s using (product_id, week) left join usual u using (product_id) left join promo p using (product_id, week)
)
select *,
       -- the retailer's promotion spend: discount given beyond the everyday card discount
       round(greatest(retailer_discount - shelf_value * usual_depth, 0), 6) as promo_spend,
       case
         when feature_share >= 0.5 and display_share >= 0.5 then 'Mailer + display'
         when feature_share >= 0.5 then 'Mailer feature'
         when display_share >= 0.5 then 'In-store display'
         when excess_depth >= {{ var('promo_depth_threshold') }} then 'Price cut only'
         else 'No promotion'
       end as promo_type
from base
