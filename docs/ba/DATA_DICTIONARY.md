# Data dictionary

Source: 84.51° *The Complete Journey* (2,469 households, 53 weeks of 2017). The raw files are loaded into DuckDB by dbt. Staging models clean and type them; the marts below feed the analysis.

## Grain and size

| Model | Grain | Rows | Used for |
|---|---|---|---|
| `stg_transactions` | One line item in one basket | 1.46M | Everything below; halo panel |
| `dim_product` | Product | 92,331 | Margin, regular price, scope |
| `fct_product_week` | Product × week (in-scope products, every week) | 413,877 | Lift model, promotion costing |
| `fct_household_week` | Household × week (every household, every week) | 130,857 | Campaign analysis, pilot sizing |
| `fct_campaign_exposure` | Household × campaign | 6,589 | Campaign analysis |

## `fct_product_week`

| Column | Type | Definition | Business rule / test |
|---|---|---|---|
| `product_id`, `week` | int | Key | Unique together; product must exist in `dim_product` |
| `units` | int | Units sold | |
| `shelf_value` | $ | Sales at regular price = net sales + retailer discount + coupon match | Reconciles to raw transactions to the cent |
| `net_sales` | $ | What shoppers paid | |
| `retailer_discount` | $ | Loyalty-card discount + retailer coupon match | Never exceeds shelf value |
| `manufacturer_coupon` | $ | Manufacturer-funded coupons | Excluded from promotion spend (the manufacturer pays) |
| `discount_depth` | share | retailer_discount ÷ shelf_value | 0–1 |
| `usual_depth` | share | The product's median discount depth across its selling weeks: its **everyday card price** | 0–1 |
| `excess_depth` | share | max(discount_depth − usual_depth, 0): the **extra discount** that week | 0–1 |
| `display_share` | share | Share of the product's sales made in stores where it was on display | 0–1 |
| `feature_share` | share | Share of the product's sales made in stores where it was in the weekly mailer | 0–1 |
| `promo_spend` | $ | max(retailer_discount − shelf_value × usual_depth, 0): discount **beyond** the everyday price | ≤ retailer_discount |
| `promo_type` | text | Mailer + display / Mailer feature / In-store display (each ≥ 50% coverage) / Price cut only (extra discount ≥ 10 pts) / No promotion | Accepted values only |

## `dim_product`

| Column | Type | Definition |
|---|---|---|
| `product_id` | int | Key (unique, not null) |
| `department`, `product_category`, `product_type`, `brand`, `manufacturer_id`, `package_size` | text/int | Product hierarchy from the source |
| `gross_margin` | share | Assumed department margin from the `margin_assumptions` seed |
| `selling_weeks` | int | Weeks with at least one sale |
| `regular_price` | $ | Median shelf price per unit |
| `in_scope` | bool | Has a margin assumption and sells in ≥ 26 weeks. The lift model further restricts to ≥ 45 weeks (core range) |

## `fct_household_week`

| Column | Type | Definition |
|---|---|---|
| `household_id`, `week` | int | Key; zero-filled so weeks without a trip appear as $0 |
| `net_sales`, `shelf_value`, `retailer_discount`, `manufacturer_coupon` | $ | As above, summed per household-week. Net sales reconcile to raw transactions |
| `trips` | int | Distinct baskets |

## `fct_campaign_exposure`

| Column | Type | Definition |
|---|---|---|
| `household_id`, `campaign_id` | int | A household targeted by a campaign |
| `campaign_type` | text | Type A (targeted, personalised), B, C |
| `start_week`, `end_week` | int | Campaign dates in transaction week numbering (week 1 starts 1 Jan 2017) |

## Assumptions (seed: `margin_assumptions`)

| Department | Gross margin on shelf price |
|---|---|
| Grocery | 25% |
| Produce | 40% |
| Meat, packaged meat, seafood | 28% |
| Deli | 40% |
| Bakery | 55% |
| Health, beauty, general merchandise, nutrition | 30% (assumption; no published figure found) |

Benchmarks from Naveo Commerce (2023) via AgMRC; tested at ±10 points.

## Derived analysis fields (Python, `out/promo_events.parquet`)

| Field | Definition |
|---|---|
| `everyday_price` | regular_price × (1 − usual_depth) |
| `unit_gp` | everyday_price × gross_margin |
| `cf_units` | Units the model predicts with no promotion (baseline) |
| `incr_units` | units − cf_units |
| `dip_units` | Change in units over the 2 weeks after (a positive value is repeat buying, credited as a gain) |
| `cannibal_units` | Units lost by rival items in the same product type |
| `incr_gp` | Margin on extra units − extra discount on those units − discount to would-buy-anyway shoppers − cannibalisation ± after-effect |
