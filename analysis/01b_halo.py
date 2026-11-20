"""Basket halo: do promotions bring extra spend on items that are NOT on promotion?

The usual objection to "promotions lose money" is that they pull shoppers in, and those shoppers fill a bigger basket.
Comparing promotion trips with other trips can't answer that, because households choose when to shop.

Shift-share design:
  * Each household's preferences are fixed from what it bought in weeks 1-26 (its share of spend on each core product).
  * From week 27 on, its promotion exposure in a week = the share of its usual basket that the retailer's promotion
    calendar happened to put on promotion that week. The calendar is set chain-wide, so exposure varies across
    households only because of what they already liked.
  * Outcome: the household's spend that week on everything NOT on promotion. Household and week fixed effects remove
    each household's normal level and chain-wide weekly swings (holidays, weather).
  * Placebo: exposure to promotions 4 weeks in the FUTURE should not move spend today.

halo $ = coefficient x exposure, summed over household-weeks; halo gross profit = halo $ x blended margin.
"""
import duckdb, json, numpy as np, pandas as pd, statsmodels.api as sm

OUT = 'out'; PRE_END = 26
con = duckdb.connect(f'{OUT}/warehouse.duckdb', read_only=True)
core = con.sql('select product_id from dim_product where selling_weeks >= 45').df().product_id
promo = con.sql("""select product_id, week, (promo_type <> 'No promotion')::int as on_promo, promo_spend
                   from fct_product_week where product_id in (select product_id from dim_product where selling_weeks >= 45)""").df()
tx = con.sql('select household_id, product_id, week, net_sales, shelf_value, basket_id from stg_transactions').df()
margin = con.sql('select product_id, coalesce(gross_margin, 0.25) as m from dim_product').df().set_index('product_id').m

# household preference weights from weeks 1-26 (core products only)
pre = tx[(tx.week <= PRE_END) & tx.product_id.isin(core)]
W = pre.pivot_table(index='household_id', columns='product_id', values='shelf_value', aggfunc='sum', fill_value=0)
W = W.div(W.sum(axis=1), axis=0)
Pm = promo.pivot(index='product_id', columns='week', values='on_promo').reindex(W.columns).fillna(0)
E = W.values @ Pm.values                                               # household x week exposure, 0..1
E = pd.DataFrame(E, index=W.index, columns=Pm.columns)

# outcome: spend on items not on promotion that week (all departments)
tx = tx.merge(promo[['product_id', 'week', 'on_promo']], on=['product_id', 'week'], how='left').fillna({'on_promo': 0})
hw = tx.groupby(['household_id', 'week']).agg(
    spend=('net_sales', 'sum'),
    nonpromo=('net_sales', lambda s: s[tx.loc[s.index, 'on_promo'] == 0].sum()),
    promo_items=('net_sales', lambda s: s[tx.loc[s.index, 'on_promo'] == 1].sum()),
    trips=('basket_id', 'nunique')).reset_index()
grid = pd.MultiIndex.from_product([W.index, range(PRE_END + 1, 54)], names=['household_id', 'week']).to_frame(index=False)
d = grid.merge(hw, on=['household_id', 'week'], how='left').fillna(0)
d['exposure'] = E.stack().reindex(pd.MultiIndex.from_frame(d[['household_id', 'week']])).values
lead = E.shift(-4, axis=1)                                             # promotions 4 weeks ahead (placebo)
d['exposure_lead4'] = lead.stack(future_stack=True).reindex(pd.MultiIndex.from_frame(d[['household_id', 'week']])).values
d = d[d.exposure_lead4.notna()].copy()

def twfe(df, y, xs):
    M = df[[y] + xs].astype(float).copy()
    for _ in range(30):
        M -= M.groupby(df.household_id.values).transform('mean')
        M -= M.groupby(df.week.values).transform('mean')
    return sm.OLS(M[y], M[xs]).fit(cov_type='cluster', cov_kwds={'groups': df.household_id.values})

res = {}
for y in ('nonpromo', 'promo_items', 'trips'):
    f = twfe(d, y, ['exposure', 'exposure_lead4'])
    res[y] = {'coef': float(f.params['exposure']), 'se': float(f.bse['exposure']),
              'lead_coef': float(f.params['exposure_lead4']), 'lead_se': float(f.bse['exposure_lead4'])}
    print(y, {k: round(v, 3) for k, v in res[y].items()})

# translate to money: halo spend over weeks 27-53 vs promotion spend in the same weeks
b, se = res['nonpromo']['coef'], res['nonpromo']['se']
exp_sum = float(d.exposure.sum())
nonpromo_margin = float((tx[tx.on_promo == 0].net_sales * tx[tx.on_promo == 0].product_id.map(margin).fillna(0.25)).sum() / tx[tx.on_promo == 0].net_sales.sum())
spend_period = float(promo[promo.week > PRE_END].promo_spend.sum())
halo_sales = b * exp_sum; halo_lo, halo_hi = (b - 1.96 * se) * exp_sum, (b + 1.96 * se) * exp_sum
out = {'household_weeks': int(len(d)), 'mean_exposure': float(d.exposure.mean()), 'sd_exposure': float(d.exposure.std()),
       'mean_nonpromo_spend': float(d.nonpromo.mean()), 'coef': res, 'nonpromo_margin': nonpromo_margin,
       'promo_spend_period': spend_period, 'halo_sales': halo_sales, 'halo_sales_lo': halo_lo, 'halo_sales_hi': halo_hi,
       'halo_gp_per_dollar': halo_sales * nonpromo_margin / spend_period,
       'halo_gp_per_dollar_lo': halo_lo * nonpromo_margin / spend_period, 'halo_gp_per_dollar_hi': halo_hi * nonpromo_margin / spend_period,
       'effect_of_10pt_more_exposure': b * 0.10}
json.dump(out, open(f'{OUT}/halo.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
