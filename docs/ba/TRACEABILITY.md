# Requirements traceability

Each requirement is traced from the business question to the data, the method, where the answer appears and how it is tested.

| Req | Story | Business question | KPI / output | Data (dbt model) | Method (script) | Shown in | Test |
|---|---|---|---|---|---|---|---|
| R1 | US-01 | Do promotions make money? | Incremental GP per $1 of promotion spend, 90% interval | `fct_product_week`, `dim_product` | Fixed-effects lift model, event costing (`01_promo_lift.py`) | Dashboard: summary tags, waterfall · Memo | `test_profit_components_add_up`, `test_waterfall_equals_headline_return` |
| R2 | US-01 | Is everyday card pricing separated from promotions? | Usual depth, excess depth, promotion spend | `fct_product_week` | SQL: median depth per product | Method doc · BRD | dbt `promo_spend_within_discount`, `share_between_0_and_1` on depths; `test_promo_spend_is_only_discount_beyond_everyday_price` |
| R3 | US-01 | Is the baseline right? | Held-out bias and error vs naive baselines | `fct_product_week` | 20% holdout of promoted weeks (`01_promo_lift.py`) | Dashboard: model check · README | `test_baseline_model_is_unbiased_on_held_out_weeks` |
| R4 | US-02 | How much supplier funding does each promotion need? | Break-even supplier share by line | — | `01_promo_lift.py` → `03_decisions.py` | Dashboard: Keep/Fix/Stop chart and table | `test_cells_cover_the_total` |
| R5 | US-03 | Which promotions to keep, fix or stop? | Verdict, reason and action per line | — | Rules in `03_decisions.py` | Dashboard table · Power BI page 3 | `test_cells_cover_the_total` (verdict values) |
| R6 | US-04 | Do promotions bring extra spend on other items? | Halo GP per $1, placebo | `stg_transactions`, `fct_product_week` | Shift-share household panel (`01b_halo.py`) | Dashboard: halo panel · Memo | `test_halo_placebo_shows_no_effect` |
| R7 | US-05 | What extra discount maximises profit? | Optimal extra discount by category and funding | — | Closed-form optimum from the depth response (`01_promo_lift.py`) | Dashboard: pricing rule table | `test_optimal_depth_is_bounded_and_rises_with_funding` |
| R8 | US-06 | Do campaigns create extra spend? | Matched DiD, placebo gap, detectable effect, break-even contact cost | `fct_household_week`, `fct_campaign_exposure` | Matched comparison, separate holdout weeks (`02_campaigns.py`) | Dashboard: campaigns · Memo | `test_campaign_detectable_effect_matches_standard_error`; placebo gap reported |
| R9 | US-06 | How big must a campaign holdout be? | Households per group by detectable lift | `fct_household_week` | Power calculation with CUPED (`03_decisions.py`) | Dashboard: plan | — |
| R10 | US-07 | How sensitive is the answer to assumptions? | Return at margin ±10 pts and funding 0–80% | `margin_assumptions` seed | Linear scenario terms (`04_export.py`) | Dashboard sliders · Power BI what-if | `test_scenario_formula_matches_full_recompute` |
| R11 | US-08 | Can it be refreshed and trusted? | Clean rebuild, identical outputs | All | `run_all.sh` | README | 19 dbt tests + 11 Python checks; deterministic rounding at thresholds; two runs give identical outputs |
