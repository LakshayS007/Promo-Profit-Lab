-- Promotion spend is the part of the discount above the everyday card discount, so it can never exceed the total discount.
select * from {{ ref('fct_product_week') }} where promo_spend > retailer_discount + 0.000001
