select product_id, manufacturer_id, department, brand, product_category, product_type, package_size
from {{ source('raw', 'products') }}
