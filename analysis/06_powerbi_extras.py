"""Extra tables for the ready-made Power BI project (powerbi/Promo_Profit_Lab_PowerBI).

Adds to powerbi/data: dim_week (date table), plan_bridge (today -> after-plan bridge per $1M),
a short action label on promo_cells_decisions, an Index on waterfall_per_dollar, and trims dim_product to promoted products.
"""
import json, pandas as pd

D = 'powerbi/data/'
s = json.load(open('out/summary.json'))

wk = pd.DataFrame({'week': range(1, 54)})
ws = pd.Timestamp('2017-01-01') + pd.to_timedelta((wk.week - 1) * 7, unit='D')
wk['week_start'] = ws.dt.strftime('%Y-%m-%d')
wk['month'] = ws.dt.strftime('%b'); wk['month_num'] = ws.dt.month
wk['quarter'] = 'Q' + ws.dt.quarter.astype(str)
wk['half'] = wk.week.map(lambda w: 'Jan-Jun' if w <= 26 else 'Jul-Dec')
wk.to_csv(D + 'dim_week.csv', index=False)

pm = s['per_million']
pd.DataFrame({'Index': [1, 2, 3],
              'step': ['Profit impact today', 'Shallower discounts on 8 Fix lines', 'Shift budget to better lines'],
              'per_million': [round(pm['incr_gp']), round(pm['depth_cut_gain']), round(pm['realloc_gain'])]}).to_csv(D + 'plan_bridge.csv', index=False)

d = pd.read_csv(D + 'promo_cells_decisions.csv')
def short(r):
    be = r.breakeven_supplier_share
    if r.verdict == 'Keep':
        return 'Keep - pays back with no funding' if be < 0.005 else f'Keep - needs {be:.0%} funding'
    if abs(r.roi_cut5 - r.roi) < 0.02:
        return f'Run only with {be:.0%} funding'
    return f'Cut 5 pts - needs {be:.0%} funding'
d['action_short'] = d.apply(short, axis=1)
d.to_csv(D + 'promo_cells_decisions.csv', index=False)

w = pd.read_csv(D + 'waterfall_per_dollar.csv')
if 'Index' not in w.columns:
    w.insert(0, 'Index', range(1, len(w) + 1))
w.to_csv(D + 'waterfall_per_dollar.csv', index=False)

ev = pd.read_csv(D + 'fact_promo_event.csv', usecols=['product_id'])
p = pd.read_csv(D + 'dim_product.csv')
p[p.product_id.isin(ev.product_id.unique())].to_csv(D + 'dim_product.csv', index=False)
print('Power BI extras written')
