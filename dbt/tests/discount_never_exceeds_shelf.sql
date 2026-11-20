select * from {{ ref('stg_transactions') }} where retailer_discount > shelf_value + 0.001
