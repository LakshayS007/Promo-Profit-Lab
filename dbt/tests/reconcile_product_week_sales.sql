-- In-scope product-week sales must equal the transaction lines for in-scope products.
select abs((select sum(net_sales) from {{ ref('fct_product_week') }})
         - (select sum(t.net_sales) from {{ ref('stg_transactions') }} t join {{ ref('dim_product') }} p using (product_id) where p.in_scope)) as diff
having diff > 0.01
