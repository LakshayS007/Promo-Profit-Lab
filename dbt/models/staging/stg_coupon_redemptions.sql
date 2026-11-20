select household_id, coupon_upc, campaign_id, redemption_date from {{ source('raw', 'coupon_redemptions') }}
