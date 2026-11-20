-- The household-week mart must add up to the cleaned transaction lines to the cent.
select abs((select sum(net_sales) from {{ ref('fct_household_week') }}) - (select sum(net_sales) from {{ ref('stg_transactions') }})) as diff
having diff > 0.01
