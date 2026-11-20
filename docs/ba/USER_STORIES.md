# User stories and acceptance criteria

Priorities use MoSCoW: **M**ust, **S**hould, **C**ould. Each story maps to a requirement in [TRACEABILITY.md](TRACEABILITY.md).

| ID | Priority | Story |
|---|---|---|
| US-01 | M | As the **CFO**, I want the incremental gross profit per $1 of promotion spend, so that I know whether the promotion budget creates or destroys value. |
| US-02 | M | As a **buyer**, I want each promotion's break-even supplier funding share, so that I can negotiate co-funding against a target. |
| US-03 | M | As a **category director**, I want every department × promotion type labelled Keep, Fix or Stop with a reason, so that I can change next quarter's calendar. |
| US-04 | M | As a **category director**, I want proof of whether promotions bring extra spend on other items, so that "promotions drive traffic" is tested, not assumed. |
| US-05 | S | As a **pricing manager**, I want the profit-maximising extra discount for each category at a given level of supplier funding, so that I can set depth by rule. |
| US-06 | S | As the **marketing manager**, I want to know whether targeted campaigns create extra spend, and how large a holdout I need to prove it, so that I can justify the campaign budget. |
| US-07 | S | As the **CFO**, I want to change the margin and supplier-funding assumptions and see the result update, so that I can judge how much the answer depends on them. |
| US-08 | C | As an **analyst**, I want the pipeline to rebuild from raw data with one command and fail loudly if numbers don't reconcile, so that I can refresh it every quarter. |

## Acceptance criteria

**US-01: profit per $1**
- *Given* the core range (products selling in ≥ 45 of 53 weeks), *when* the analysis runs, *then* it reports incremental gross profit per $1 of promotion spend with a 90% interval.
- *Given* a product with an everyday card discount, *when* promotion spend is calculated, *then* only discount beyond its usual level is counted.
- *Then* the profit components (margin on extra units, discount on extra units, discount to would-buy-anyway shoppers, cannibalisation, after-effect) add up exactly to the total.

**US-02: break-even funding**
- *Given* a department × promotion type with at least $1,000 of promotion spend and 30 events, *then* its break-even supplier share = max(0, −return per $1).
- *When* the supplier-funding slider is set to X%, *then* each line shows whether it pays back at X%.

**US-03: Keep / Fix / Stop**
- Keep if break-even funding ≤ 25%.
- Stop if break-even funding > 50% and the category's household penetration is below the median.
- Otherwise Fix, with a specific action: shallower extra discount and the funding share required.
- Every line shows its verdict, the reason and the action in one row.

**US-04: halo**
- *Given* household purchase shares fixed from weeks 1–26, *when* weekly exposure to the promotion calendar is computed for weeks 27–53, *then* the effect on spend on non-promoted items is estimated with household and week fixed effects.
- *Then* a placebo using promotions 4 weeks in the future shows no effect (|t| < 2).
- *Then* the halo is reported per $1 of promotion spend, with a 95% interval.

**US-05: pricing rule**
- *For* each category and supplier share in {0, 25, 50, 75}%, *then* the optimal extra discount is reported, together with today's average extra discount.

**US-06: campaigns**
- *Then* three estimates are shown side by side: naive, matched on the same weeks, and matched with separate holdout weeks.
- *Then* the smallest effect detectable at 80% power and the break-even cost per household contact are reported.
- *Then* the number of households per group needed to detect a 2%, 3%, 5% and 10% lift is listed, with and without CUPED.

**US-07: assumptions**
- Margin is adjustable by ±10 points and supplier funding from 0% to 80%. Totals, verdicts and "pays back?" update immediately.

**US-08: reproducibility**
- `./run_all.sh` rebuilds every output from raw data. All dbt tests and Python checks pass, and two runs give identical results.
