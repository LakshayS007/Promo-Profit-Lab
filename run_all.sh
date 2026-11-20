#!/usr/bin/env bash
# Rebuilds everything from raw data: warehouse, tests, analysis, dashboard and Power BI tables. Run from the repo root.
set -euo pipefail
[ -f data/raw/transactions.parquet ] || python data/get_data.py
mkdir -p out
echo "== 1 build and test the warehouse (dbt + DuckDB)"; (cd dbt && dbt build --profiles-dir .)
echo "== 2 promotion lift and incremental profit";      python analysis/01_promo_lift.py
echo "== 2b basket halo (shift-share household panel)"; python analysis/01b_halo.py
echo "== 3 campaign impact (matched comparison)";        python analysis/02_campaigns.py
echo "== 4 keep/fix/stop, optimiser, pilot design";      python analysis/03_decisions.py
echo "== 5 dashboard data and Power BI tables";          python analysis/04_export.py
echo "== 6 dashboard -> docs/index.html";                python analysis/05_build_dashboard.py
echo "== 7 Power BI project tables";                   python analysis/06_powerbi_extras.py
echo "== 8 checks";                                      python -m pytest -q tests
