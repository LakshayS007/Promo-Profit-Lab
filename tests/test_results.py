"""Checks that the outputs are internally consistent. Run with: python -m pytest -q tests"""
import json, pandas as pd, numpy as np, duckdb

def test_profit_components_add_up():
    ev = pd.read_csv('powerbi/data/fact_promo_event.csv')
    parts = ev.margin_on_incremental - ev.promo_spend - ev.dip_gp - ev.cannibal_gp
    assert np.allclose(parts, ev.incr_gp, atol=1e-6)

def test_waterfall_equals_headline_return():
    d = json.load(open('out/dashboard_data.json'))
    assert abs(sum(w['per_dollar'] for w in d['waterfall']) - d['summary']['roi']) < 1e-9

def test_scenario_formula_matches_full_recompute():
    s = json.load(open('out/summary.json')); sens = pd.read_csv('out/sensitivity.csv')
    r = sens[(sens.margin_shift == 0) & (sens.vendor_share == 0.5)].iloc[0]
    assert abs(s['incr_gp'] + 0.5 * s['promo_spend'] - r.incr_gp) < 1.0

def test_cells_cover_the_total():
    # decision lines need >= 30 events and >= $1,000 of spend; together they must cover at least 95% of promotion spend
    c = pd.read_csv('out/decisions.csv'); s = json.load(open('out/summary.json'))
    assert abs(c.promo_spend.sum() - s['promo_spend_in_cells']) < 1e-6
    assert c.promo_spend.sum() >= 0.95 * s['promo_spend']
    assert set(c.verdict) <= {'Keep', 'Fix', 'Kill'}

def test_optimiser_keeps_budget_and_kills():
    c = pd.read_csv('out/decisions.csv')
    assert abs(c.spend_optimised.sum() - c.promo_spend.sum()) < 1e-3
    assert (c.loc[c.verdict == 'Kill', 'spend_optimised'] == 0).all()

def test_warehouse_reconciles_to_raw():
    con = duckdb.connect('out/warehouse.duckdb', read_only=True)
    a = con.sql('select sum(net_sales) from fct_household_week').fetchall()[0][0]
    b = con.sql("select sum(sales_value) from 'data/raw/transactions.parquet' where quantity > 0").fetchall()[0][0]
    assert abs(a - b) < 0.01

def test_promo_spend_is_only_discount_beyond_everyday_price():
    ev = pd.read_csv('powerbi/data/fact_promo_event.csv')
    assert (ev.promo_spend >= -1e-9).all()
    assert (ev.excess_depth >= -1e-9).all() and (ev.usual_depth.between(0, 1)).all()
    assert np.allclose(ev.disc_on_baseline + ev.disc_on_incremental, ev.promo_spend, atol=1e-6)

def test_baseline_model_is_unbiased_on_held_out_weeks():
    v = json.load(open('out/summary.json'))['validation']
    assert abs(v['model_bias']) < 0.05
    assert v['model_wape'] < v['naive_no_lift_wape']

def test_halo_placebo_shows_no_effect():
    h = json.load(open('out/halo.json'))['coef']['nonpromo']
    assert abs(h['lead_coef'] / h['lead_se']) < 2

def test_optimal_depth_is_bounded_and_rises_with_funding():
    o = pd.read_csv('out/optimal_depth.csv')
    assert o.optimal_extra_discount.between(0, 0.5).all()
    assert (o.sort_values('supplier_share').groupby('group').optimal_extra_discount.apply(lambda x: x.is_monotonic_increasing)).all()

def test_campaign_detectable_effect_matches_standard_error():
    c = pd.read_csv('out/campaigns_by_type.csv')
    assert np.allclose(c.mde_80, 2.8 * c.se)
