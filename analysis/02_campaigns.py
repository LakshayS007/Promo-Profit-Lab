"""Stage A: did targeted campaigns cause extra spend, or did they just reach households that already spend a lot?

For every campaign that starts in week 13 or later (so there are at least 8 matching weeks plus 4 holdout weeks):
  1. Treated = households in the campaign.
  2. Controls = households in no campaign during the 4 weeks before it or while it runs.
  3. Each treated household is matched (nearest neighbour, with replacement) to the control household with the most similar
     spend level, trip count and spend trend over the MATCHING weeks (week 1 to 5 weeks before the start). Treated households
     with no close control can be dropped with a caliper (tested; it discarded most households without fixing the placebo gap).
  4. Difference-in-differences on weekly spend: campaign weeks vs the 4 HOLDOUT weeks just before the start, treated minus
     matched controls. Measuring against weeks that were not used for matching removes the regression-to-the-mean bias that
     matching on noisy spend would otherwise add.
  5. Placebo check: in the holdout weeks (no campaign yet, not used for matching) treated and matched households should
     spend the same. A large gap there would mean the matching failed.
Results are pooled by campaign type, with 95% intervals from a household bootstrap.
"""
import duckdb, json, numpy as np, pandas as pd

OUT = 'out'; PRE = 4; MIN_MATCH = 8; CALIPER = np.inf;   # a 0.5 caliper was tested: it dropped 60-90% of treated households and did not close the placebo gap
rng = np.random.default_rng(11)
con = duckdb.connect(f'{OUT}/warehouse.duckdb', read_only=True)
hw = con.sql('select household_id, week, net_sales, trips, manufacturer_coupon, retailer_discount from fct_household_week').df()
S = hw.pivot(index='household_id', columns='week', values='net_sales').fillna(0)
T = hw.pivot(index='household_id', columns='week', values='trips').fillna(0)
ex = con.sql('select * from fct_campaign_exposure').df()
camps = ex.groupby(['campaign_id', 'campaign_type']).agg(start=('start_week', 'first'), end=('end_week', 'first'), n=('household_id', 'size')).reset_index()
# retailer-funded coupon match cost actually redeemed by treated households during each campaign
cm = con.sql("""select r.campaign_id, sum(t.coupon_match_discount) as match_cost, sum(t.manufacturer_coupon) as mfr_coupon, count(*) as lines
               from stg_coupon_redemptions r join stg_transactions t
                 on t.household_id = r.household_id and cast(t.transaction_timestamp as date) = r.redemption_date
               group by 1""").df()

rows, gaps = [], []
for c in camps.itertuples():
    if c.start - PRE - 1 < MIN_MATCH: continue                     # not enough history before the campaign
    end = min(c.end, 53); pre = list(range(c.start - PRE, c.start)); post = list(range(c.start, end + 1))
    mwin = list(range(1, c.start - PRE))                           # matching weeks, kept separate from the holdout weeks
    treated = ex.loc[ex.campaign_id == c.campaign_id, 'household_id'].unique()
    busy = ex[(ex.start_week <= end) & (ex.end_week >= c.start - PRE)].household_id.unique()
    controls = np.setdiff1d(S.index.values, busy)
    treated = np.intersect1d(treated, S.index.values)
    if len(treated) < 10 or len(controls) < 50: continue
    def feats(ids):
        s = S.loc[ids, mwin].values; t = T.loc[ids, mwin].values
        slope = np.polyfit(np.arange(len(mwin)), s.T, 1)[0]
        return np.c_[s.mean(1), t.mean(1), slope, s[:, -4:].mean(1)]
    Ft, Fc = feats(treated), feats(controls)
    mu, sd = Fc.mean(0), Fc.std(0) + 1e-9
    D = (((Ft - mu) / sd)[:, None, :] - ((Fc - mu) / sd)[None, :, :]) ** 2
    dist = np.sqrt(D.sum(2)); best = dist.argmin(1); dmin = dist[np.arange(len(treated)), best]
    keep = dmin <= CALIPER                                          # only keep treated households with a genuinely similar control
    n_all = len(treated); treated = treated[keep]; match = controls[best[keep]]
    if len(treated) < 10: continue
    dt = S.loc[treated, post].mean(axis=1).values - S.loc[treated, pre].mean(axis=1).values
    dc = S.loc[match, post].mean(axis=1).values - S.loc[match, pre].mean(axis=1).values
    diff = dt - dc                                                 # per-household DiD in $ per week
    # for comparison: (1) naive gap vs all controls during the campaign, (2) the tempting version that matches and
    # measures on the same 8 pre-weeks (exposed to regression to the mean)
    naive = S.loc[treated, post].values.mean() - S.loc[controls, post].values.mean()
    w8 = list(range(c.start - 8, c.start)); f8 = lambda ids: np.c_[S.loc[ids, w8].mean(axis=1), T.loc[ids, w8].mean(axis=1), S.loc[ids, w8[-4:]].mean(axis=1)]
    a8, b8 = f8(treated), f8(controls); m8 = controls[((((a8 - b8.mean(0)) / (b8.std(0) + 1e-9))[:, None, :] - ((b8 - b8.mean(0)) / (b8.std(0) + 1e-9))[None]) ** 2).sum(2).argmin(1)]
    same_window = ((S.loc[treated, post].mean(axis=1).values - S.loc[treated, w8].mean(axis=1).values)
                   - (S.loc[m8, post].mean(axis=1).values - S.loc[m8, w8].mean(axis=1).values)).mean()
    wk = list(range(c.start - PRE, end + 1))
    gap = S.loc[treated, wk].values - S.loc[match, wk].values
    gaps.append(pd.DataFrame({'campaign_id': c.campaign_id, 'campaign_type': c.campaign_type, 'rel_week': np.array(wk) - c.start,
                              'gap': gap.mean(0) - gap[:, :PRE].mean()}))
    pre_slope = np.polyfit(np.arange(PRE), gap[:, :PRE].mean(0), 1)[0]
    rows.append({'campaign_id': c.campaign_id, 'campaign_type': c.campaign_type, 'start_week': c.start, 'weeks': len(post),
                 'households': len(treated), 'matched_share': len(treated) / n_all, 'controls': len(controls), 'pre_spend_treated': S.loc[treated, pre].values.mean(),
                 'pre_spend_matched': S.loc[match, pre].values.mean(), 'pre_spend_all_controls': S.loc[controls, pre].values.mean(),
                 'naive_gap': naive, 'same_window_did': same_window, 'placebo_gap_pct': S.loc[treated, pre].values.mean() / S.loc[match, pre].values.mean() - 1,
                 'did_per_hh_week': diff.mean(), 'pre_trend_slope': pre_slope, '_diff': diff})
R = pd.DataFrame(rows)

def pooled(g):
    d = np.concatenate(g._diff.values); w = np.concatenate([np.full(len(x), wks) for x, wks in zip(g._diff, g.weeks)])
    boots = [np.average(d[i], weights=w[i]) for i in (rng.integers(0, len(d), len(d)) for _ in range(2000))]
    est = np.average(d, weights=w)
    hh_weeks = float((g.households * g.weeks).sum())
    return pd.Series({'campaigns': len(g), 'households_exposures': int(g.households.sum()),
                      'matched_share': float((g.households).sum() / (g.households / g.matched_share).sum()), 'household_weeks': hh_weeks,
                      'did_per_hh_week': est, 'lo': np.quantile(boots, .025), 'hi': np.quantile(boots, .975),
                      'pre_spend_treated': np.average(g.pre_spend_treated, weights=g.households),
                      'pre_spend_all_controls': np.average(g.pre_spend_all_controls, weights=g.households),
                      'pre_spend_matched': np.average(g.pre_spend_matched, weights=g.households),
                      'max_abs_pre_slope': g.pre_trend_slope.abs().max(),
                      'naive_gap': np.average(g.naive_gap, weights=g.households * g.weeks),
                      'same_window_did': np.average(g.same_window_did, weights=g.households * g.weeks),
                      'placebo_gap_pct': np.average(g.placebo_gap_pct, weights=g.households),
                      'did_pct_of_spend': est / np.average(g.pre_spend_treated, weights=g.households),
                      'gp_per_household_contact': est * float((g.weeks * g.households).sum()) / float(g.households.sum()),
                      'incremental_sales': est * hh_weeks, 'incremental_sales_lo': np.quantile(boots, .025) * hh_weeks,
                      'incremental_sales_hi': np.quantile(boots, .975) * hh_weeks})
P = R.groupby('campaign_type').apply(pooled, include_groups=False).reset_index()
blend = con.sql("""select sum(t.shelf_value * coalesce(p.gross_margin, 0.25)) / sum(t.shelf_value) from stg_transactions t
                   join dim_product p using (product_id)""").fetchall()[0][0]
cost = cm[cm.campaign_id.isin(R.campaign_id)].merge(camps[['campaign_id', 'campaign_type']], on='campaign_id').groupby('campaign_type')[['match_cost', 'mfr_coupon']].sum()
P = P.join(cost, on='campaign_type')
P['blended_margin'] = blend
P['incremental_gp'] = P.incremental_sales * blend - P.match_cost.fillna(0)
P['incremental_gp_lo'] = P.incremental_sales_lo * blend - P.match_cost.fillna(0)
P['incremental_gp_hi'] = P.incremental_sales_hi * blend - P.match_cost.fillna(0)
P['gp_per_household_contact'] = P.gp_per_household_contact * blend - P.match_cost.fillna(0) / P.households_exposures   # break-even contact cost
P['selection_gap_pct'] = P.pre_spend_treated / P.pre_spend_all_controls - 1      # how much more targeted households already spent
G = pd.concat(gaps); G = G.groupby(['campaign_type', 'rel_week']).gap.mean().reset_index()
R.drop(columns='_diff').to_csv(f'{OUT}/campaigns_by_campaign.csv', index=False)
P.to_csv(f'{OUT}/campaigns_by_type.csv', index=False); G.to_csv(f'{OUT}/campaign_event_study.csv', index=False)
pd.set_option('display.width', 250)
print(R.drop(columns='_diff').round(2).to_string()); print(P.round(3).T.to_string()); print('blended margin', round(blend, 3))
