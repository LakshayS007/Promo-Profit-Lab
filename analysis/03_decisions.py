"""Stages C-F: turn the estimates into decisions.

C. Margin and supplier-funding sensitivity (computed in 01, summarised here).
D. Keep / Fix / Kill for every department-group x promotion-type cell.
E. Budget reallocation: same total promotion budget, moved between cells to maximise incremental gross profit
   (a linear programme with guardrails; returns are assumed constant within 50-150% of today's spend).
F. Pilot design: sample size for a randomised campaign holdout.
"""
import json, numpy as np, pandas as pd, duckdb
from scipy.optimize import linprog
from statsmodels.stats.power import TTestIndPower

OUT = 'out'
cells = pd.read_csv(f'{OUT}/promo_cells.csv'); meta = json.load(open(f'{OUT}/lift_meta.json'))
camp = pd.read_csv(f'{OUT}/campaigns_by_type.csv'); sens = pd.read_csv(f'{OUT}/sensitivity.csv')
halo = json.load(open(f'{OUT}/halo.json')); opt = pd.read_csv(f'{OUT}/optimal_depth.csv')

# ---------- D. Keep / Fix / Kill
KEEP_MAX_FUNDING = 0.25      # pays back already, or once suppliers fund at most a quarter of the extra discount
TRAFFIC = cells.traffic_penetration.median()
STOP_MIN_FUNDING = 0.50      # needs suppliers to fund more than half the extra discount
def verdict(r):
    if r.breakeven_supplier_share <= KEEP_MAX_FUNDING: return 'Keep'
    if r.breakeven_supplier_share > STOP_MIN_FUNDING and r.traffic_penetration < TRAFFIC: return 'Kill'
    return 'Fix'
def action(r):
    if r.verdict == 'Keep': return 'Keep. Pays back with no supplier funding.' if r.roi >= 0 else f'Keep. Pays back once suppliers fund {r.breakeven_supplier_share:.0%} of the extra discount.'
    if r.verdict == 'Fix':
        bits = []
        if r.roi_cut5 > r.roi + 0.03: bits.append(f'cut the extra discount by 5 pts (loss per $1 falls from {-r.roi*100:.0f}¢ to {-r.roi_cut5*100:.0f}¢)')
        bits.append(f'only run with at least {r.breakeven_supplier_share:.0%} supplier funding')
        return 'Fix: ' + '; '.join(bits) + '.'
    return f'Stop unless a supplier funds {r.breakeven_supplier_share:.0%}+ of it. Low traffic role and {r.subsidised_share:.0%} of units would sell anyway.'
cells['verdict'] = cells.apply(verdict, axis=1); cells['action'] = cells.apply(action, axis=1)

# ---------- E. Budget optimiser (linear programme)
# Each cell returns roi per $ of discount. Spend can move between cells but stays within 50%-150% of today's level
# (returns are only trusted near what was observed), traffic-driving cells keep at least 80%, Kill cells go to zero,
# and total spend is unchanged.
s0 = cells.promo_spend.values; roi = cells.roi.values
lo = np.where(cells.traffic_penetration >= TRAFFIC, 0.8, 0.5) * s0; hi = 1.5 * s0
kill = (cells.verdict == 'Kill').values
lo[kill] = 0; hi[kill] = 0                    # Kill cells stop (unless a supplier funds them), and their budget moves elsewhere
res = linprog(-roi, A_eq=[np.ones(len(s0))], b_eq=[s0.sum()], bounds=list(zip(lo, hi)), method='highs')
cells['spend_optimised'] = res.x
cells['spend_change'] = res.x - s0
gain = float(roi @ res.x - roi @ s0)
# combined plan: reallocate + shallower discounts on Fix cells
fix = cells.verdict == 'Fix'
cut_gain = float((cells.incr_gp_cut5 - cells.incr_gp)[fix & (cells.roi_cut5 > cells.roi + 0.03)].sum())

# ---------- F. Pilot design: randomised holdout for targeted campaigns
con = duckdb.connect(f'{OUT}/warehouse.duckdb', read_only=True)
hw = con.sql('select household_id, week, net_sales from fct_household_week').df()
six = hw.assign(block=(hw.week - 1) // 6).groupby(['household_id', 'block']).net_sales.mean().reset_index()
sd6, mean6 = six.net_sales.std(), six.net_sales.mean()
# CUPED: adjusting each household's test-period spend by its own previous 6 weeks removes the predictable part of the noise
w = six.pivot(index='household_id', columns='block', values='net_sales')
rho = float(np.nanmean([w[b].corr(w[b - 1]) for b in range(1, w.columns.max() + 1)]))
an = TTestIndPower()
pilot = []
for lift in (0.02, 0.03, 0.05, 0.10):
    d = lift * mean6 / sd6
    n = an.solve_power(effect_size=d, alpha=0.05, power=0.8, alternative='two-sided')
    pilot.append({'detectable_lift': lift, 'households_per_arm': int(np.ceil(n)), 'households_per_arm_cuped': int(np.ceil(n * (1 - rho ** 2)))})
pilot = pd.DataFrame(pilot)

total_spend = float(s0.sum())
# campaigns: smallest effect the data could have detected, and the most a contact could cost and still pay back
camp['se'] = (camp.hi - camp.lo) / 3.92
camp['mde_80'] = 2.8 * camp.se
camp['weeks_per_contact'] = camp.household_weeks / camp.households_exposures
camp['gp_per_contact'] = camp.did_per_hh_week * camp.weeks_per_contact * camp.blended_margin
camp['gp_per_contact_hi'] = camp.hi * camp.weeks_per_contact * camp.blended_margin
camp.to_csv(f'{OUT}/campaigns_by_type.csv', index=False)
PER_M = 1_000_000 / meta['promo_spend']                # results per $1M of promotion spend
summary = {
    'products': meta['products'], 'promo_weeks': meta['promo_weeks'], 'shelf_value': meta['shelf_value'],
    'promo_spend': meta['promo_spend'], 'promo_spend_in_cells': total_spend, 'incr_gp': meta['incr_gp'], 'roi': meta['roi'], 'roi_lo': meta['roi_lo'], 'roi_hi': meta['roi_hi'],
    'subsidised_share': meta['subsidised_share'], 'lift_pct': meta['lift_pct'], 'breakeven_supplier_share': -meta['roi'],
    'optimiser_gain': gain, 'optimiser_gain_per_100': gain / total_spend * 100, 'depth_cut_gain': cut_gain,
    'combined_gain': gain + cut_gain, 'combined_gain_pct_of_loss': (gain + cut_gain) / -meta['incr_gp'],
    'per_million': {'incr_gp': meta['incr_gp'] * PER_M, 'combined_gain': (gain + cut_gain) * PER_M, 'realloc_gain': gain * PER_M,
                    'depth_cut_gain': cut_gain * PER_M, 'stop_kill_saving': float(-cells.loc[cells.verdict == 'Kill', 'incr_gp'].sum()) * PER_M},
    'stop_kill_saving': float(-cells.loc[cells.verdict == 'Kill', 'incr_gp'].sum()),
    'everyday_share_of_discount': meta['everyday_share_of_discount'], 'all_card_discount_core': meta['all_card_discount_core'],
    'validation': meta['validation'], 'halo': {k: halo[k] for k in ('halo_gp_per_dollar', 'halo_gp_per_dollar_lo', 'halo_gp_per_dollar_hi', 'coef', 'mean_exposure')},
    'roi_with_halo_upper': meta['roi'] + halo['halo_gp_per_dollar_hi'],
    'optimal_depth': opt.to_dict('records'),
    'campaign_economics': camp.set_index('campaign_type')[['mde_80', 'gp_per_contact', 'gp_per_contact_hi', 'weeks_per_contact']].to_dict('index'),
    'verdict_counts': cells.verdict.value_counts().to_dict(),
    'campaign_selection_gap': camp.set_index('campaign_type').selection_gap_pct.to_dict(),
    'campaign_did': camp.set_index('campaign_type')[['naive_gap', 'same_window_did', 'did_per_hh_week', 'lo', 'hi', 'placebo_gap_pct']].to_dict('index'),
    'pilot': pilot.to_dict('records'), 'cuped_rho': rho, 'six_week_mean_spend': mean6, 'six_week_sd': sd6,
    'sensitivity': sens.to_dict('records'), 'traffic_threshold': float(TRAFFIC), 'keep_max_funding': KEEP_MAX_FUNDING,
}
cells.to_csv(f'{OUT}/decisions.csv', index=False); pilot.to_csv(f'{OUT}/pilot_design.csv', index=False)
json.dump(summary, open(f'{OUT}/summary.json', 'w'), indent=1, default=float)
pd.set_option('display.width', 250)
print(cells[['group', 'promo_type', 'roi', 'breakeven_supplier_share', 'traffic_penetration', 'verdict', 'promo_spend', 'spend_optimised']].round(3).to_string())
print(json.dumps({k: v for k, v in summary.items() if k not in ('sensitivity',)}, indent=1, default=float))
