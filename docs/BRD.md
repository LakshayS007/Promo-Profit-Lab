# Business Requirements: Promotion ROI and Budget Allocation

*Version 2. Simulated engagement: the stakeholders and process are illustrative; the data and every number are real.*

| | |
|---|---|
| **Business owner** | Category Director (decision), CFO (budget sign-off) |
| **Analyst** | Lakshay Saini |
| **Decision to support** | Which promotions to keep, redesign or stop next quarter; how much supplier funding to ask for; how to split a fixed promotion budget |
| **Data** | 84.51° *The Complete Journey*: 2,469 households, every grocery purchase over 53 weeks of 2017, weekly mailer and display placement, 27 campaigns and coupons |

## 1. Problem

The retailer gives back about 15% of shelf value as loyalty-card discounts. Promotions are judged on sales uplift, which hides four costs:
- discount given to shoppers who would have bought anyway;
- the discount on the extra units themselves;
- sales taken from rival items in the same category;
- stock-up buying that lowers sales in the weeks after.

A fifth problem sits in the books. **About half of all card discounts on core products (51%) are the product's everyday card price, not a promotion.** Counting them as promotion cost overstates spend and blames the wrong lines.

Nobody can say which promotions make money, or what supplier funding each one needs.

## 2. Questions to answer

| # | Question | Stakeholder |
|---|---|---|
| Q1 | What is the incremental gross profit per $1 of promotion spend, by promotion type and department? | CFO |
| Q2 | What share of the extra discount must a supplier fund for each promotion to break even? | Category Director, buying team |
| Q3 | Which promotions should we keep, fix or stop? | Category Director |
| Q4 | Do promotions bring extra spend on other items (the "traffic" argument)? | Category Director |
| Q5 | What extra discount maximises profit for a given level of supplier funding? | Pricing |
| Q6 | Do targeted campaigns create extra spend, and how big a holdout is needed to prove it? | Marketing |
| Q7 | How should next quarter's budget be split, and how do we test the change before rolling it out? | CFO, Marketing |

## 3. KPI definitions

| KPI | Definition |
|---|---|
| Shelf value | Sales at regular price: net sales + retailer discount + coupon match |
| Usual (everyday) discount | The product's median card discount depth across the year |
| Extra discount | Discount depth that week minus the usual depth (0 if below) |
| Promotion spend | Retailer-funded discount **beyond** the everyday price. Manufacturer coupons are excluded (the manufacturer pays) |
| Baseline units | Units the product would have sold that week without the promotion (model estimate) |
| Subsidised share | Baseline units ÷ actual units in promoted weeks |
| Incremental gross profit (iGP) | Margin on extra units − extra discount on those units − extra discount to would-buy-anyway shoppers − margin taken from rival items ± change in the 2 weeks after |
| Return per $1 | iGP ÷ promotion spend |
| Break-even supplier funding | Share of promotion spend a supplier must fund for iGP to reach zero (= −return per $1 when negative) |
| Halo | Change in a household's spend on non-promoted items when more of its usual basket is on promotion |
| Traffic role | Share of panel households that buy the department group at least once |
| Campaign effect | Weekly spend change (campaign weeks vs 4 separate holdout weeks) for targeted households minus matched non-targeted households |

## 4. Promotion types (product-week)

| Type | Rule |
|---|---|
| Mailer + display | In the weekly mailer and on display, each in stores covering ≥ 50% of the product's sales |
| Mailer feature | In the mailer in stores covering ≥ 50% of the product's sales |
| In-store display | On display in stores covering ≥ 50% of the product's sales |
| Price cut only | No mailer or display, but an extra discount of ≥ 10 points beyond the everyday price |
| No promotion | Everything else |

## 5. Assumptions

| Assumption | Value | Why | Tested |
|---|---|---|---|
| Gross margin on shelf price | Grocery 25%, produce 40%, meat 28%, deli 40%, bakery 55%, health and GM 30% | No cost data. Benchmarks from Naveo Commerce (2023) via AgMRC | ±10 points |
| Supplier funding | 0% in the base case | Not in the data | 0–80% slider |
| Baseline range | Products selling in ≥ 45 of 53 weeks | Stable baseline; 59% of in-scope sales | — |
| Price-cut threshold | 10 points of extra discount | Separates promotions from normal price noise | — |

## 6. Scope

| In scope | Out of scope |
|---|---|
| Promotion profit by department group × type | Mailing and print costs |
| Supplier break-even and optimal extra discount | Store-level operations and labour |
| Basket halo (shift-share household panel) | Competitor prices (not in the data) |
| Targeted campaign effect, holdout sizing | Long-run brand or loyalty effects beyond 2 weeks |

## 7. Deliverables

| Deliverable | Audience |
|---|---|
| One-page CEO memo | CEO, CFO |
| Interactive dashboard with supplier-funding and margin sliders | Category Director, buying team |
| Executive deck (7 slides) | Leadership meeting |
| Power BI report built from the exported tables | Finance and category analysts |
| Process maps, user stories, traceability, data dictionary ([docs/ba](ba/)) | Project team |
| Tested SQL models (dbt) and Python analysis, reproducible end to end | Analytics team |

## 8. Acceptance criteria

Full Given/When/Then criteria are in [USER_STORIES.md](ba/USER_STORIES.md); each is traced in [TRACEABILITY.md](ba/TRACEABILITY.md).

- Every mart reconciles to raw transactions to the cent (dbt tests).
- Profit components add up to the total for every promotion event (Python test).
- The baseline model is checked on held-out promotion weeks and beats naive baselines on bias.
- Results are shown with intervals and with margin and supplier-funding sensitivity.
- Every recommendation names its value, its risk and how to test it.
