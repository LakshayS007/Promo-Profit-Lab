-- Weekly in-store display and mailer (feature) placement by product and store. '0' means not promoted.
-- The raw table has some duplicate product-store-week rows (caught by the share tests), so collapse to one row each.
select product_id, store_id, week,
       bool_or(display_location <> '0') as on_display,
       bool_or(mailer_location  <> '0') as in_mailer,
       bool_or(mailer_location in ('D','F','H','L','Z')) as front_or_back_page
from {{ source('raw', 'promotions') }}
group by 1, 2, 3
