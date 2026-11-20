-- Products with their assumed department margin, regular shelf price and whether they are in the lift-model scope.
with sales as (
    select product_id,
           count(distinct week)                       as selling_weeks,
           sum(quantity)                              as units,
           sum(shelf_value)                           as shelf_value,
           median(shelf_value / quantity)             as regular_price
    from {{ ref('stg_transactions') }}
    group by 1
)
select p.*, m.gross_margin, s.selling_weeks, s.units, s.shelf_value, s.regular_price,
       (m.gross_margin is not null and s.selling_weeks >= {{ var('min_selling_weeks') }}) as in_scope
from {{ ref('stg_products') }} p
left join {{ ref('margin_assumptions') }} m using (department)
left join sales s using (product_id)
