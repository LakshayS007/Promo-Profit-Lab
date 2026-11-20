# Build the Power BI report (about 90 minutes)

> **Ready-made version:** `powerbi/Promo_Profit_Lab_PowerBI/` is the finished 5-page report as a Power BI Project (`.pbip`).
> Open `Promo_Profit_Lab.pbip` in Power BI Desktop, then **Home → Transform data → Edit parameters → DataFolder** and set it to this repo's `powerbi\data\` folder (ending with `\`), and click **Refresh**.
> The guide below explains how to build the same thing by hand.


Everything the report needs is already computed and saved in `powerbi/data/`. Power BI only loads, relates and visualises it, so the numbers will match the dashboard and the memo exactly.

**You need:** Power BI Desktop (free, Windows). Optional: a Power BI service account to publish online.

## 1. Load the data (10 min)

1. **Home → Get data → Text/CSV.** Load each file in `powerbi/data/`.
2. For `fact_promo_event.csv`, click **Transform data** and check that `week` is a whole number and the money columns are decimal numbers. Then click **Close & Apply**.

| File | Role | Rows |
|---|---|---|
| `fact_promo_event.csv` | Fact: one row per promoted product-week, with every profit component, usual and extra discount depth, and everyday price | ~23.6k |
| `dim_product.csv` | Product attributes | ~7.8k |
| `promo_cells_decisions.csv` | One row per department × promotion type: verdict, action, break-even funding, optimised spend | 14 |
| `campaign_results.csv` | Campaign effect by type under three methods, smallest detectable effect, gross profit per contact | 3 |
| `optimal_depth.csv` | Profit-maximising extra discount by department and supplier share, with today's extra discount | 24 |
| `campaign_event_study.csv` | Weekly gap before and after campaigns | 45 |
| `waterfall_per_dollar.csv` | Where $1 of promotion spend goes | 5 |
| `sensitivity.csv`, `pilot_design.csv` | Margin and supplier scenarios; pilot sample sizes | small |
| `param_supplier_share.csv`, `param_margin_shift.csv` | What-if slicer values | 21 each |

## 2. Model view: relationships (5 min)

| From | To | Cardinality |
|---|---|---|
| `fact_promo_event[product_id]` | `dim_product[product_id]` | Many to one |
| `fact_promo_event[cell_key]` | `promo_cells_decisions[cell_key]` | Many to one |

Leave the parameter, campaign, waterfall, depth and pilot tables unrelated.

## 3. Measures (10 min)

1. **Home → Enter data**, name the table `_Measures`, then **Load**.
2. Add each measure from `measures.dax` (**Modeling → New measure**, paste, Enter).
3. Formats:
   - `Return per $1`: currency, 2 decimals.
   - `Subsidised Share`, `Lift %` and `Break-even Supplier Share`: percentage, 0 decimals.

## 4. Pages (60 min)

**Theme:** **View → Themes → Customize current theme.** Set the background to light grey `#F4F5F2`, use `#FFD43B` (shelf-tag yellow) for card backgrounds on page 1, and use `#2A78D6`, `#EB6834` and `#1BAF7A` for data colours.

### Page 1: Summary

| Visual | Fields |
|---|---|
| 4 cards | `Return per $1`, `Subsidised Share`, `Break-even Supplier Share`, `Matched Holdout (correct)` filtered to Type A |
| Waterfall chart | Category: `waterfall_per_dollar[step]`. Y: `per_dollar`. Sort in file order |
| Text box | The question: "Which promotions actually make money?" |

### Page 2: Promotion types

| Visual | Fields |
|---|---|
| Clustered bar | Axis: `fact_promo_event[promo_type]`. Value: `Return per $1` |
| Clustered bar | Axis: `promo_type`. Value: `Subsidised Share` |
| Matrix | Rows: `group`. Columns: `promo_type`. Values: `Return per $1`, with conditional formatting (diverging, centre 0) |

### Page 3: Keep or fix (the interactive page)

| Visual | Fields |
|---|---|
| 2 slicers (single select) | `param_supplier_share[supplier_share_pct]`, `param_margin_shift[margin_shift_pts]` |
| Cards | `Scenario Incremental GP`, `Scenario Return per $1`, `Lines Paying Back` |
| Scatter | X: `promo_cells_decisions[breakeven_supplier_share]`. Y: `traffic_penetration`. Size: `promo_spend`. Legend: `verdict`. Tooltip: `action` |
| Table | `cell_key`, `verdict`, `breakeven_supplier_share`, `Pays Back?`, `Scenario Incremental GP`, `action` |

### Page 4: Campaigns

| Visual | Fields |
|---|---|
| Clustered bar | Axis: `campaign_type`. Values: `Naive Gap`, `Matched Same-Window`, `Matched Holdout (correct)` |
| Line chart | `campaign_event_study`: X `rel_week`, Y `gap`, Legend `campaign_type`. Add a constant line at X = 0 for the campaign start |
| Table | `campaign_type`, `Matched Holdout (correct)`, `Smallest Detectable Effect`, `GP per Contact (upper bound)` |
| Text box | Three sentences on why the naive number is wrong (copy from the dashboard) |

### Page 5: Discount depth

| Visual | Fields |
|---|---|
| Matrix | Rows: `optimal_depth[group]`. Columns: `supplier_share`. Values: `Best Extra Discount`, with a sequential colour scale |
| Clustered bar | Axis: `group`. Values: `Extra Discount Today`, `Best Extra Discount`, filtered to supplier share 0.5 |

### Page 6: Plan

| Visual | Fields |
|---|---|
| Table | `promo_cells_decisions`: `cell_key`, `promo_spend`, `spend_optimised` (today vs optimised budget) |
| Table | `pilot_design` |
| Text box | The three actions from `docs/CEO_MEMO.md` |

## 5. Share it (5 min)

| Option | How |
|---|---|
| **Public link** (best for a portfolio) | **Publish → My workspace**, then in the Power BI service: **File → Embed report → Publish to web**. Paste the link in the README. Some organisations switch this off; a personal account usually works |
| **PDF** | **File → Export → PDF**. Save it as `powerbi/Promo_Profit_Lab.pdf` and commit it |
| **Screenshots** | Save one image per page to `docs/screenshots/powerbi-*.png` and add them to the README |

Commit the `.pbix` file too (`powerbi/Promo_Profit_Lab.pbix`), but most reviewers can't open it. The PDF and screenshots are what they'll actually look at.

## Check before you share

- [ ] Page 1 `Return per $1` shows **−$0.33**, the same as the dashboard.
- [ ] `Incremental GP per $1M` shows about **−$327k**.
- [ ] With the supplier slider at 50%, `Scenario Incremental GP` is about **+$28.8k**.
- [ ] The scatter shows 14 points: 6 Keep, 8 Fix.
- [ ] Page 5 shows a best extra discount of 0 for every department at 0% and 25% supplier funding.
