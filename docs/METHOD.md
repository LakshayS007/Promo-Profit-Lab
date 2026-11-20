# Method

## 1. Data model (dbt + DuckDB)

| Layer | Models | Notes |
|---|---|---|
| Staging | `stg_transactions`, `stg_products`, `stg_promotions`, `stg_campaigns`, `stg_coupon_redemptions`, `stg_households` | Splits discounts into retailer-funded (loyalty, coupon match) and manufacturer-funded (coupons). Rebuilds shelf value. Drops 8,869 zero-quantity lines. Collapses 12,785 duplicate product-store-week rows in the promotions table (found by the share tests) |
| Seed | `margin_assumptions` | Department gross margins, with source |
| Marts | `dim_product`, `fct_product_week`, `fct_household_week`, `fct_campaign_exposure` | Product × week grid includes zero-sales weeks. Display and mailer coverage is weighted by where each product actually sells. Shares are rounded to 9 digits so threshold tests give the same answer on every run |
| Tests | 19 | Uniqueness, relationships, accepted values, shares between 0 and 1, discount never above shelf value, promotion spend never above the discount, both marts reconcile to raw sales to the cent |

Column definitions: [ba/DATA_DICTIONARY.md](ba/DATA_DICTIONARY.md).

## 2. Separating promotions from everyday pricing

Many products carry a loyalty-card discount almost every week. That is their normal price, not a promotion. Version 1 counted it as promotion cost, which overstated spend and labelled ordinary weeks as "price cuts".

| Term | Definition |
|---|---|
| Usual depth | The product's median discount depth over its selling weeks |
| Extra discount | Depth that week − usual depth (floored at 0) |
| Promotion spend | max(retailer discount − shelf value × usual depth, 0) |
| Price-cut promotion | Extra discount ≥ 10 points and no mailer or display |
| Everyday price | Regular price × (1 − usual depth). Margin is earned on this price |

Result: **51% of card discounts on core products are everyday pricing.** Promotion spend on the core range is $166k, not $354k.

## 3. Promotion lift (`analysis/01_promo_lift.py`)

Unit: product × week, for the 2,186 products that sold in at least 45 of 53 weeks (115,858 product-weeks; 59% of in-scope shelf value).

```
log(1 + units_it) = product_i + department×week_t
                  + β[group, type] · promo_type_it
                  + γ[group] · extra_discount_it
                  + δ1 · promoted_last_week_it + δ2 · promoted_two_weeks_ago_it
                  + θ · rival_promo_share_it + ε_it
```

| Term | What it captures | Estimate |
|---|---|---|
| Product fixed effects | Each product's normal sales level | absorbed |
| Department × week fixed effects | Seasonality, holidays, store traffic | absorbed |
| β | Lift from mailer, display or both, by department group | Grocery mailer + display ×1.99; deli display ×3.37; grocery price cut alone ×1.00 |
| γ | Lift per point of extra discount, by department group | Grocery +24% per 10 points; deli +10% |
| δ1, δ2 | After-effect in the 2 weeks after a promotion | +4.5% and +2.7%: **repeat buying, not stock-up dips** |
| θ | Cannibalisation from rivals in the same product type | −6.3% when all rivals are promoted |

Fixed effects are removed by alternating demeaning. Standard errors are clustered by product. Within-R² is 0.17.

**Costing each promoted product-week:**

| Component | Formula |
|---|---|
| Baseline units | (units + 1) · exp(−effect) − 1, × smearing factor |
| Margin on extra units | extra units × everyday price × margin |
| Extra discount | promotion spend, split between baseline units (would-buy-anyway) and extra units |
| Cannibalisation | units lost by rivals × their everyday unit margin |
| After-effect | change in units over the next 2 weeks × unit margin (a gain when positive) |
| iGP | margin on extra units − extra discount − cannibalisation + after-effect |

Intervals come from 300 draws of the coefficient vector from its clustered sampling distribution.

**Why fixed effects, not a before/after comparison?** Retailers time promotions for seasonal peaks. Department × week effects remove the season, so the promotion is not credited with Christmas.

## 4. Model check (held-out promoted weeks)

One in five promotion events (4,709) was removed before fitting, then predicted.

| Baseline | Bias in total units | WAPE |
|---|---|---|
| This model | −1.8% | 43.7% |
| No lift (normal-week sales) | −54.0% | 61.6% |
| One average uplift for every promotion | −0.6% | 42.8% |

The log model under-predicted by 16% before correction. That is the usual retransformation bias of a log model. Duan's smearing factor (1.15) removes it.

A single average uplift is as accurate in total, but it cannot rank promotions. The model's predicted lifts correlate 0.56 with actual lifts on held-out events, and it separates the would-buy-anyway, cannibalisation and after-effect terms the profit calculation needs.

## 5. Basket halo (`analysis/01b_halo.py`)

**Question:** when promotions bring a shopper in, do they buy more of everything else?

Comparing promotion trips with other trips is biased, because households choose when to shop. So the test uses a **shift-share design**:

| Step | Detail |
|---|---|
| Preferences | Each household's share of spend on each core product, fixed from weeks 1–26 |
| Exposure | Weeks 27–53: the share of that household's usual basket the chain's promotion calendar put on promotion that week (mean 23%, SD 14%) |
| Outcomes | Spend on non-promoted items; spend on promoted items; trips |
| Model | Household and week fixed effects, standard errors clustered by household; 53,866 household-weeks |
| Placebo | Exposure 4 weeks in the future, which should have no effect |

| Per 10 points more exposure | Effect a week | 95% interval |
|---|---|---|
| Spend on promoted items | +$0.38 | +$0.32 to +$0.44 |
| Spend on everything else | −$0.09 | −$0.28 to +$0.10 |
| Placebo (everything else, 4 weeks ahead) | +$0.04 | −$0.21 to +$0.29 |
| Trips | +0.011 | +0.005 to +0.018 |

In money: −4¢ of gross profit per $1 of promotion spend (95%: −11¢ to +4¢). Even the upper end leaves promotions at −29¢.

## 6. Campaigns (`analysis/02_campaigns.py`)

| Step | Detail |
|---|---|
| Campaigns | 20 that start in week 13 or later: 3 Type A, 13 Type B, 4 Type C |
| Controls | Households in no campaign from 4 weeks before the start to the end |
| Matching | Nearest neighbour, with replacement, on mean weekly spend, trips, spend trend and recent spend in the **matching weeks** (week 1 to 5 weeks before the start) |
| Effect | Difference-in-differences: campaign weeks vs the 4 **holdout weeks** just before the start |
| Placebo | Treated vs matched spend in the holdout weeks, which matching never saw |
| Interval | Household bootstrap, 2,000 draws |
| Detectable effect | 2.8 × bootstrap standard error (80% power, 5% two-sided) |
| Gross profit per contact | Effect × campaign weeks per contact × blended margin, before the cost of the contact |

Matching and measuring on the same 8 weeks gives +$6.84 a week for Type A. That is regression to the mean: controls matched on an unusually high stretch of spending drift back down, which flatters the campaign. Separating the matching weeks from the measurement weeks gives +$0.34 (95%: −$1.14 to +$1.82), below the detectable effect of $2.12. Type B comes out negative, but its placebo gap is 16%, so it is reported as inconclusive.

## 7. Decisions (`analysis/03_decisions.py`)

A decision line is a department group × promotion type with at least 30 events and $1,000 of promotion spend (14 lines, 98.5% of spend).

| Step | Method |
|---|---|
| Keep | Break-even supplier funding ≤ 25% |
| Stop | Break-even > 50% and household penetration below the median (none qualifies) |
| Fix | Everything else, with a specific action: 5-point shallower extra discount and the funding share required |
| Shallower discount | Re-cost every event with the extra discount cut by 5 points, using the estimated depth response |
| Optimal extra discount | Maximise margin on volume minus discount cost: d* = m / (1 − v) − 1 / γ, capped at 0–50%, for supplier share v |
| Budget optimiser | Linear programme (`scipy.optimize.linprog`, HiGHS): maximise Σ return × spend with total spend fixed. Each line stays within 50–150% of today's spend (80% floor for traffic lines); Stop lines go to zero |
| Per $1M | Every dollar figure ÷ promotion spend × $1M, so the result reads the same for a business of any size |
| Pilot | Two-sample power calculation on 6-week household spend (mean $35.17, SD $43.06). CUPED uses the correlation between consecutive 6-week blocks (ρ = 0.84) |

Return is linear in supplier funding (return(v) = return(0) + v), so the reallocation gain does not depend on the funding assumption.

## 8. Limitations

- **No cost data.** Margins are benchmarks and are tested ±10 points.
- **Supplier funding is not observed.** The base case assumes the retailer pays the whole extra discount.
- **Panel data.** The 2,469 households are a sample of the retailer's customers, not total store sales.
- **Zero-sales weeks.** Price-cut status is unknown when nothing sold. Restricting to products with ≥ 45 selling weeks keeps this small.
- **Optimal depth extrapolates** beyond observed depths at high supplier funding; 50% is a cap, not a recommendation.
- **Campaign targeting is non-random.** Matching cannot remove selection on things we don't see; only a randomised holdout can.
- **Effects beyond 2 weeks** (long-run loyalty, price image) are not measured.
