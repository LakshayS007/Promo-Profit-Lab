"""Injects the dashboard data into the page template.
Writes out/dashboard.html (body-only, for hosting as a Claude artifact) and docs/index.html (full standalone page for GitHub Pages)."""
import json, os
data = open('out/dashboard_data.json').read()
t = open('analysis/dashboard_template.html').read().replace('__DATA__', data)
open('out/dashboard.html', 'w', encoding='utf-8').write(t)
os.makedirs('docs', exist_ok=True)
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n')
nos = ('<noscript><div style="margin:16px;padding:14px 18px;border-radius:8px;background:#ffd43b;color:#16191d;font:600 15px system-ui">'
       'This dashboard needs JavaScript. Download the file and open it in Chrome, Edge, Safari or Firefox.</div></noscript>\n')
open('docs/index.html', 'w', encoding='utf-8').write(head + t.replace('<header class="wrap mast">', nos + '<header class="wrap mast">', 1))
print('dashboard', len(t) // 1024, 'KB')
