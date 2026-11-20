"""Exports: dashboard data (JSON) and Power BI tables (CSV)."""
import json, os, numpy as np, pandas as pd, duckdb

OUT = 'out'; PBI = 'powerbi/data'; os.makedirs(PBI, exist_ok=True)
ev = pd.read_parquet(f'{OUT}/promo_events.parquet')
cells = pd.read_csv(f'{OUT}/decisions.csv'); S = json.load(open(f'{OUT}/summary.json'))
types = pd.read_csv(f'{OUT}/promo_types.csv'); camp = pd.read_csv(f'{OUT}/campaigns_by_type.csv')
es = pd.read_csv(f'{OUT}/campaign_event_study.csv')
con = duckdb.connect(f'{OUT}/warehouse.duckdb', read_only=True)
price = con.sql('select product_id, regular_price, gross_margin from dim_product').df()
ev = ev.merge(price, on='product_id', how='left')
halo = json.load(open(f'{OUT}/halo.json')); opt = pd.read_csv(f'{OUT}/optimal_depth.csv')
u = ev.units.replace(0, np.nan)
ev['disc_on_baseline'] = (ev.promo_spend * ev.cf_units / u).fillna(0)
ev['disc_on_incremental'] = ev.promo_spend - ev.disc_on_baseline
ev['margin_on_incremental'] = ev.incr_units * ev.unit_gp
ev['dip_gp'] = ev.dip_units * ev.unit_gp            # negative = margin gained in the weeks after (repeat buying)
ev['cannibal_gp'] = ev.cannibal_units * ev.unit_gp
# linear scenario terms: incr_gp(margin shift dm, supplier share v) = A + K*dm + v*spend
ev['K'] = (ev.incr_units - ev.dip_units - ev.cannibal_units) * ev.everyday_price
check = (ev.margin_on_incremental - ev.promo_spend - ev.dip_gp - ev.cannibal_gp - ev.incr_gp).abs().max()
assert check < 1e-6, check

def agg(g):
    return pd.Series({k: g[k].sum() for k in ['promo_spend', 'incr_gp', 'margin_on_incremental', 'disc_on_baseline', 'disc_on_incremental',
                                              'dip_gp', 'cannibal_gp', 'K', 'units', 'cf_units', 'incr_units', 'shelf_value']} | {'events': len(g)})
cell_terms = ev.groupby(['group', 'promo_type']).apply(agg, include_groups=False).reset_index()
cells = cells.merge(cell_terms[['group', 'promo_type', 'K', 'margin_on_incremental', 'disc_on_baseline', 'disc_on_incremental', 'dip_gp', 'cannibal_gp']], on=['group', 'promo_type'])
tot = agg(ev)
waterfall = [
    {'step': 'Margin on extra units sold', 'value': tot.margin_on_incremental},
    {'step': 'Extra discount on those extra units', 'value': -tot.disc_on_incremental},
    {'step': 'Extra discount to shoppers who would have bought anyway', 'value': -tot.disc_on_baseline},
    {'step': 'Margin taken from rival items (cannibalisation)', 'value': -tot.cannibal_gp},
    {'step': 'Repeat buying in the weeks after', 'value': -tot.dip_gp},
]
per = lambda x: float(x / tot.promo_spend)
dash = {
    'summary': S | {'K_total': float(tot.K), 'A_total': float(tot.incr_gp)},
    'waterfall': [{'step': w['step'], 'per_dollar': per(w['value']), 'value': float(w['value'])} for w in waterfall],
    'types': types[['promo_type', 'events', 'promo_spend', 'incr_gp', 'roi', 'roi_lo', 'roi_hi', 'subsidised_share', 'lift_pct']].to_dict('records'),
    'cells': cells[['group', 'promo_type', 'events', 'promo_spend', 'incr_gp', 'roi', 'roi_lo', 'roi_hi', 'roi_cut5', 'incr_gp_cut5',
                    'subsidised_share', 'lift_pct', 'breakeven_supplier_share', 'traffic_penetration', 'verdict', 'action',
                    'spend_optimised', 'K']].to_dict('records'),
    'campaigns': camp[['campaign_type', 'campaigns', 'households_exposures', 'naive_gap', 'same_window_did', 'did_per_hh_week', 'lo', 'hi',
                       'placebo_gap_pct', 'pre_spend_treated', 'pre_spend_all_controls', 'selection_gap_pct', 'mde_80', 'gp_per_contact',
                       'gp_per_contact_hi', 'weeks_per_contact']].to_dict('records'),
    'event_study': es.to_dict('records'),
    'halo': halo, 'optimal_depth': opt.to_dict('records'),
}
json.dump(dash, open(f'{OUT}/dashboard_data.json', 'w'), default=float)

# ---------- Power BI tables
ev.assign(cell_key=ev.group + ' | ' + ev.promo_type)[['cell_key', 'product_id', 'week', 'department', 'group', 'product_type', 'promo_type', 'discount_depth', 'usual_depth', 'excess_depth', 'units', 'cf_units', 'incr_units',
    'dip_units', 'cannibal_units', 'shelf_value', 'promo_spend', 'margin_on_incremental', 'disc_on_baseline', 'disc_on_incremental',
    'dip_gp', 'cannibal_gp', 'incr_gp', 'regular_price', 'everyday_price', 'gross_margin', 'K']].to_csv(f'{PBI}/fact_promo_event.csv', index=False)
con.sql('select product_id, department, brand, product_category, product_type, gross_margin, regular_price from dim_product where in_scope').df().to_csv(f'{PBI}/dim_product.csv', index=False)
cells.assign(cell_key=cells.group + ' | ' + cells.promo_type).to_csv(f'{PBI}/promo_cells_decisions.csv', index=False)
camp.to_csv(f'{PBI}/campaign_results.csv', index=False)
es.to_csv(f'{PBI}/campaign_event_study.csv', index=False)
pd.read_csv(f'{OUT}/sensitivity.csv').to_csv(f'{PBI}/sensitivity.csv', index=False)
pd.read_csv(f'{OUT}/pilot_design.csv').to_csv(f'{PBI}/pilot_design.csv', index=False)
pd.DataFrame({'supplier_share_pct': range(0, 101, 5)}).to_csv(f'{PBI}/param_supplier_share.csv', index=False)
pd.DataFrame({'margin_shift_pts': range(-10, 11)}).to_csv(f'{PBI}/param_margin_shift.csv', index=False)
pd.DataFrame(dash['waterfall']).to_csv(f'{PBI}/waterfall_per_dollar.csv', index=False)
opt.to_csv(f'{PBI}/optimal_depth.csv', index=False)
print('waterfall per $1:', [(w['step'][:30], round(per(w['value']), 3)) for w in waterfall], 'total', round(per(tot.incr_gp), 3))
print('files', os.listdir(PBI))
