-- One row per basket line. sales_value is what the retailer received after the loyalty discount and coupon match.
select
    household_id, store_id, basket_id, product_id, week,
    transaction_timestamp,
    quantity,
    sales_value                                         as net_sales,
    retail_disc                                         as loyalty_discount,      -- funded by the retailer
    coupon_match_disc                                   as coupon_match_discount, -- funded by the retailer
    coupon_disc                                         as manufacturer_coupon,   -- funded by the manufacturer, not a retailer cost
    retail_disc + coupon_match_disc                     as retailer_discount,
    sales_value + retail_disc + coupon_match_disc       as shelf_value            -- value at regular shelf price
from {{ source('raw', 'transactions') }}
where quantity > 0 and sales_value >= 0
