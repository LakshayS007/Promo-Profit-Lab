"""Stage B: true promotion lift and incremental gross profit.

Model (one row per product-week; core range = products selling in 45+ of 53 weeks):

    log(1 + units_it) = a_i + g_(dept,t)                          product and department-week fixed effects
                      + b_(group,type) * promo_type_it             lift by department group and promotion type
                      + c_group * excess_depth_it                  extra lift per point of discount beyond the usual card discount
                      + d1 * promoted_(t-1) + d2 * promoted_(t-2)  after-effect: pantry loading (dip) or repeat buying (gain)
                      + q * rival_promo_share_it                   cannibalisation by other items of the same product type
                      + e_it

Everyday card pricing is part of the product's normal price: each product's usual discount is its baseline, and only
discount beyond it is promotion spend (see dbt/models/marts/fct_product_week.sql).

Fixed effects are absorbed by alternating demeaning; standard errors are clustered by product. Every promoted
product-week is then costed: gross profit actually made, minus what it would have made with no promotion, minus margin
lost in the dip weeks and margin taken from rival items.

Validation: 20% of promoted product-weeks are held out, the model is refitted without them, and their units are
predicted. Error is compared with two naive baselines.
"""
import duckdb, json, numpy as np, pandas as pd, statsmodels.api as sm

OUT = 'out'
rng = np.random.default_rng(7)
con = duckdb.connect(f'{OUT}/warehouse.duckdb', read_only=True)
pw = con.sql("""select f.*, p.department, p.product_type, p.gross_margin, p.regular_price, p.units as annual_units
                from fct_product_week f join dim_product p using (product_id) where p.selling_weeks >= 45""").df()
GROUP = {'GROCERY': 'Grocery', 'PRODUCE': 'Produce', 'MEAT': 'Fresh meat', 'MEAT-PCKGD': 'Packaged meat & seafood',
         'SEAFOOD-PCKGD': 'Packaged meat & seafood', 'DELI': 'Deli & bakery', 'PASTRY': 'Deli & bakery',
         'DRUG GM': 'Health, beauty & GM', 'NUTRITION': 'Health, beauty & GM'}
TYPES = ['Price cut only', 'Mailer feature', 'In-store display', 'Mailer + display']
pw['group'] = pw.department.map(GROUP)
pw = pw.sort_values(['product_id', 'week']).reset_index(drop=True)
pw['everyday_price'] = pw.regular_price * (1 - pw.usual_depth)       # what the product normally sells for, after the card discount
pw['promo'] = (pw.promo_type != 'No promotion').astype(float)
pw['depth'] = pw.excess_depth.clip(0, 0.9) * pw.promo
g = pw.groupby('product_id').promo
pw['lag1'] = g.shift(1).fillna(0) * (1 - pw.promo)
pw['lag2'] = g.shift(2).fillna(0) * (1 - pw.promo) * (1 - pw['lag1'])
pw['w_annual'] = pw.annual_units
tw = pw.assign(pu=pw.promo * pw.w_annual).groupby(['product_type', 'week']).agg(tp=('pu', 'sum'), tu=('w_annual', 'sum')).reset_index()
pw = pw.merge(tw, on=['product_type', 'week'], how='left')
pw['rival_share'] = ((pw.tp - pw.promo * pw.w_annual) / (pw.tu - pw.w_annual)).where(pw.tu > pw.w_annual, 0).fillna(0)
pw['y'] = np.log1p(pw.units)
pw['dw'] = pw.department + '_' + pw.week.astype(str)

cols = []
for grp in sorted(pw.group.unique()):
    for t in TYPES:
        c = f'{grp}|{t}'; pw[c] = ((pw.group == grp) & (pw.promo_type == t)).astype(float); cols.append(c)
    c = f'{grp}|depth'; pw[c] = pw.depth * (pw.group == grp); cols.append(c)
cols += ['lag1', 'lag2', 'rival_share']
cols = [c for c in cols if pw[c].abs().sum() > 0]

def fit_fe(df, cols, iters=40):
    """OLS with product and department-week fixed effects absorbed by alternating demeaning."""
    M = df[['y'] + cols].astype(float).copy()
    for _ in range(iters):
        M -= M.groupby(df.product_id.values).transform('mean')
        M -= M.groupby(df.dw.values).transform('mean')
    return sm.OLS(M.y, M[cols]).fit(cov_type='cluster', cov_kwds={'groups': df.product_id.values})

def fixed_effects(df, beta, iters=60):
    """Recover the product and department-week effects given the slopes, for prediction."""
    r = df.y.values - df[beta.index].values @ beta.values
    a = pd.Series(0.0, index=df.product_id.unique()); gdw = pd.Series(0.0, index=df.dw.unique())
    for _ in range(iters):
        a = pd.Series(r - gdw.reindex(df.dw).values, index=df.product_id.values).groupby(level=0).mean()
        gdw = pd.Series(r - a.reindex(df.product_id).values, index=df.dw.values).groupby(level=0).mean()
    return a, gdw

fit = fit_fe(pw, cols)
beta, V = fit.params, fit.cov_params()
print(fit.summary().tables[1])

# ---------- out-of-sample check: hold out 20% of promoted weeks, refit, predict them
promo_idx = pw.index[pw.promo == 1].values
hold = rng.choice(promo_idx, size=len(promo_idx) // 5, replace=False)
train = pw.drop(index=hold)
fit_tr = fit_fe(train, cols)
a, gdw = fixed_effects(train, fit_tr.params)
H = pw.loc[hold]
ok = H.product_id.isin(a.index) & H.dw.isin(gdw.index)
H = H[ok]
lin = a.reindex(H.product_id).values + gdw.reindex(H.dw).values + H[fit_tr.params.index].values @ fit_tr.params.values
# Duan smearing: exp of a log-scale prediction estimates the median, not the mean, so rescale by the mean exp(residual)
res_tr = train.y.values - (a.reindex(train.product_id).values + gdw.reindex(train.dw).values + train[fit_tr.params.index].values @ fit_tr.params.values)
smear = float(np.mean(np.exp(res_tr)))
pred_raw = np.expm1(lin).clip(0)
pred = (np.exp(lin) * smear - 1).clip(0)
# lift check: within held-out events, does the model rank promotions' lift correctly? compare predicted vs actual
# units relative to each product's own no-promotion average

# naive 1: "no lift" = the product's average units in its non-promoted training weeks
base_mean = train[train.promo == 0].groupby('product_id').units.mean()
naive_none = base_mean.reindex(H.product_id).fillna(0).values
# naive 2: the product's average units in its other promoted training weeks
promo_mean = train[train.promo == 1].groupby('product_id').units.mean()
naive_promo = promo_mean.reindex(H.product_id).values; naive_promo = np.where(np.isnan(naive_promo), naive_none, naive_promo)
wape = lambda p: float(np.abs(H.units.values - p).sum() / H.units.values.sum())
bias = lambda p: float(p.sum() / H.units.values.sum() - 1)
act_ratio = H.units.values / np.maximum(naive_none, 1e-9); pred_ratio = pred / np.maximum(naive_none, 1e-9)
okr = naive_none > 0
from scipy.stats import spearmanr
validation = {'held_out_events': int(len(H)), 'smearing_factor': smear, 'model_wape': wape(pred), 'model_bias': bias(pred),
              'model_wape_no_smearing': wape(pred_raw), 'model_bias_no_smearing': bias(pred_raw),
              'lift_rank_corr': float(spearmanr(act_ratio[okr], pred_ratio[okr]).statistic),
              'naive_no_lift_wape': wape(naive_none), 'naive_no_lift_bias': bias(naive_none),
              'naive_avg_promo_wape': wape(naive_promo), 'naive_avg_promo_bias': bias(naive_promo)}
print('validation', json.dumps(validation, indent=1))

def economics(b, vendor_share=0.0, margin_shift=0.0, depth_cut=0.0, df=pw):
    """Incremental gross profit for every promoted product-week, given a coefficient vector b."""
    d = df[df.promo == 1].copy()
    if depth_cut:   # what if every price-led promotion ran a shallower extra discount?
        cvec = np.array([b.get(f'{g}|depth', 0) for g in d.group])
        new = np.maximum(d.depth.values - depth_cut, 0)
        u_new = np.maximum((d.units.values + 1) * np.exp(cvec * (new - d.depth.values)) - 1, 0)
        ratio = np.where(d.depth.values > 0, new / np.maximum(d.depth.values, 1e-9), 1)
        scale = np.where(d.units.values > 0, u_new / np.maximum(d.units.values, 1e-9), 1)
        d = d.assign(promo_spend=d.promo_spend.values * scale * ratio, shelf_value=d.shelf_value.values * scale, units=u_new, depth=new)
    eff = np.array([b.get(f'{g}|{t}', 0) for g, t in zip(d.group, d.promo_type)]) + np.array([b.get(f'{g}|depth', 0) for g in d.group]) * d.depth.values
    m = (d.gross_margin + margin_shift).clip(0.05, 0.9).values
    unit_gp = d.everyday_price.values * m                                   # margin per unit at the everyday price
    cf = np.maximum((d.units.values + 1) * np.exp(-eff) - 1, 0)             # units it would have sold anyway
    spend = d.promo_spend.values * (1 - vendor_share)
    gp_actual = d.units.values * unit_gp - spend
    gp_cf = cf * unit_gp
    nxt = df.set_index(['product_id', 'week'])
    dip = np.zeros(len(d))
    for lag, key in ((1, 'lag1'), (2, 'lag2')):
        idx = list(zip(d.product_id, d.week + lag))
        u = nxt.units.reindex(idx).values; flag = nxt[key].reindex(idx).fillna(0).values
        dip += np.nan_to_num((u + 1) * (np.exp(-b.get(key, 0)) - 1)) * flag
    w_i = (d.w_annual / d.tu).values
    tu_week = df.groupby(['product_type', 'week']).units.sum()
    other_units = tu_week.reindex(list(zip(d.product_type, d.week))).values - d.units.values
    cannibal = np.maximum(other_units, 0) * (np.exp(-b.get('rival_share', 0) * w_i) - 1)
    # not clipped: a negative 'dip' is a post-promotion gain (repeat buying), which is credited to the promotion
    lost_gp = (dip + cannibal) * unit_gp
    return d.assign(cf_units=cf, incr_units=d.units.values - cf, dip_units=dip, cannibal_units=cannibal, unit_gp=unit_gp,
                    promo_spend=spend, gp_actual=gp_actual, gp_cf=gp_cf, lost_gp=lost_gp, incr_gp=gp_actual - gp_cf - lost_gp)

def summarise(d, keys):
    s = d.groupby(keys).agg(events=('incr_gp', 'size'), units=('units', 'sum'), cf_units=('cf_units', 'sum'),
                            incr_units=('incr_units', 'sum'), dip_units=('dip_units', 'sum'), cannibal_units=('cannibal_units', 'sum'),
                            promo_spend=('promo_spend', 'sum'), incr_gp=('incr_gp', 'sum'), shelf_value=('shelf_value', 'sum'),
                            excess_depth=('depth', 'mean')).reset_index()
    s['subsidised_share'] = s.cf_units / s.units
    s['lift_pct'] = s.incr_units / s.cf_units
    s['roi'] = s.incr_gp / s.promo_spend
    s['breakeven_supplier_share'] = (-s.roi).clip(lower=0)
    return s

base = economics(beta)
pen = con.sql("""select p.product_type, count(distinct t.household_id) * 1.0 / (select count(distinct household_id) from stg_transactions) as penetration
                 from stg_transactions t join dim_product p using (product_id) group by 1""").df()
base = base.merge(pen, on='product_type', how='left')
cells = summarise(base, ['group', 'promo_type'])
tr = base.groupby(['group', 'promo_type']).apply(lambda x: np.average(x.penetration, weights=x.shelf_value + 1e-9), include_groups=False).rename('traffic_penetration')
cells = cells.join(tr, on=['group', 'promo_type'])
MIN_SPEND = 1000
cells = cells[(cells.events >= 30) & (cells.promo_spend >= MIN_SPEND)].reset_index(drop=True)   # too little spend to judge
types = summarise(base, ['promo_type']); total = summarise(base.assign(all='All'), ['all'])

draws = rng.multivariate_normal(beta.values, V.values, size=300)
sims_c, sims_t, sims_all = [], [], []
for dr in draws:
    b = pd.Series(dr, index=beta.index); e = economics(b)
    sims_c.append(summarise(e, ['group', 'promo_type']).set_index(['group', 'promo_type']).roi)
    sims_t.append(summarise(e, ['promo_type']).set_index('promo_type').roi)
    sims_all.append(e.incr_gp.sum() / e.promo_spend.sum())
sc, st = pd.concat(sims_c, axis=1), pd.concat(sims_t, axis=1)
cells = cells.join(sc.quantile(0.05, axis=1).rename('roi_lo'), on=['group', 'promo_type']).join(sc.quantile(0.95, axis=1).rename('roi_hi'), on=['group', 'promo_type'])
types = types.join(st.quantile(0.05, axis=1).rename('roi_lo'), on='promo_type').join(st.quantile(0.95, axis=1).rename('roi_hi'), on='promo_type')

sens = []
for ms in (-0.10, -0.05, 0, 0.05, 0.10):
    for vs in (0.0, 0.25, 0.5):
        e = economics(beta, vendor_share=vs, margin_shift=ms)
        sens.append({'margin_shift': ms, 'vendor_share': vs, 'roi': e.incr_gp.sum() / economics(beta, margin_shift=ms).promo_spend.sum(), 'incr_gp': e.incr_gp.sum()})
sens = pd.DataFrame(sens)
cell_sens = pd.concat([summarise(economics(beta, margin_shift=ms), ['group', 'promo_type'])[['group', 'promo_type', 'roi']].assign(margin_shift=ms) for ms in (-0.10, 0, 0.10)])
cut = summarise(economics(beta, depth_cut=0.05), ['group', 'promo_type'])[['group', 'promo_type', 'incr_gp', 'promo_spend', 'roi']]
cells = cells.merge(cut.rename(columns={'incr_gp': 'incr_gp_cut5', 'promo_spend': 'promo_spend_cut5', 'roi': 'roi_cut5'}), on=['group', 'promo_type'], how='left')

# ---------- optimal extra discount by group, for a given supplier share v
# gross profit per baseline unit, as a share of the everyday price: f(d) = exp(b + c*d) * (m - d*(1-v)) - m
# df/dd = 0  ->  d* = m/(1-v) - 1/c   (clipped to 0..50%; when d* = 0 the best price-led promotion is no extra discount)
opt = []
for grp in sorted(pw.group.unique()):
    c_ = beta.get(f'{grp}|depth', np.nan); se = fit.bse.get(f'{grp}|depth', np.nan)
    m_ = float(np.average(pw.loc[pw.group == grp, 'gross_margin'], weights=pw.loc[pw.group == grp, 'shelf_value'] + 1e-9))
    for v in (0, 0.25, 0.5, 0.75):
        d_star = float(np.clip(m_ / (1 - v) - 1 / c_, 0, 0.5)) if c_ > 0 else 0.0
        opt.append({'group': grp, 'supplier_share': v, 'depth_coef': c_, 'depth_coef_se': se, 'margin': m_,
                    'optimal_extra_discount': d_star, 'current_extra_discount': float(pw.loc[(pw.group == grp) & (pw.promo == 1) & (pw.depth > 0), 'depth'].mean())})
opt = pd.DataFrame(opt)

coef = pd.DataFrame({'coef': beta, 'se': fit.bse, 'lift_multiplier': np.exp(beta)})
coef.to_csv(f'{OUT}/lift_coefficients.csv')
cells.to_csv(f'{OUT}/promo_cells.csv', index=False); types.to_csv(f'{OUT}/promo_types.csv', index=False)
sens.to_csv(f'{OUT}/sensitivity.csv', index=False); cell_sens.to_csv(f'{OUT}/cell_sensitivity.csv', index=False)
opt.to_csv(f'{OUT}/optimal_depth.csv', index=False)
base[['product_id', 'week', 'department', 'group', 'product_type', 'penetration', 'promo_type', 'discount_depth', 'usual_depth', 'excess_depth',
      'units', 'cf_units', 'incr_units', 'dip_units', 'cannibal_units', 'shelf_value', 'everyday_price', 'unit_gp', 'promo_spend',
      'retailer_discount', 'gp_actual', 'gp_cf', 'lost_gp', 'incr_gp']].to_parquet(f'{OUT}/promo_events.parquet', index=False)
everyday = con.sql("""select sum(f.retailer_discount) total_disc, sum(f.promo_spend) promo_spend,
                      sum(case when p.selling_weeks >= 45 then f.retailer_discount end) core_disc,
                      sum(case when p.selling_weeks >= 45 then f.promo_spend end) core_promo
                      from fct_product_week f join dim_product p using (product_id)""").df().iloc[0].to_dict()
meta = {'products': int(pw.product_id.nunique()), 'product_weeks': int(len(pw)), 'promo_weeks': int(pw.promo.sum()),
        'shelf_value': float(pw.shelf_value.sum()), 'promo_spend': float(base.promo_spend.sum()),
        'all_card_discount_core': float(everyday['core_disc']), 'everyday_share_of_discount': 1 - float(everyday['core_promo']) / float(everyday['core_disc']),
        'incr_gp': float(base.incr_gp.sum()), 'roi': float(total.roi.iloc[0]),
        'roi_lo': float(np.quantile(sims_all, .05)), 'roi_hi': float(np.quantile(sims_all, .95)),
        'subsidised_share': float(total.subsidised_share.iloc[0]), 'lift_pct': float(total.lift_pct.iloc[0]),
        'dip': {'lag1': float(beta.get('lag1', 0)), 'lag2': float(beta.get('lag2', 0))}, 'rival': float(beta.get('rival_share', 0)),
        'r2_within': float(fit.rsquared), 'validation': validation}
json.dump(meta, open(f'{OUT}/lift_meta.json', 'w'), indent=1)
pd.set_option('display.width', 220)
print(types.round(3).to_string()); print(cells.round(3).to_string()); print(sens.round(3).to_string()); print(opt.round(3).to_string())
print(json.dumps({k: v for k, v in meta.items()}, indent=1))
