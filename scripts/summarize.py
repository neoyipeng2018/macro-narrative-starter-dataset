#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

def read_tsv(name: str):
    path = ROOT / name
    if not path.exists():
        return []
    with path.open(newline='') as f:
        return list(csv.DictReader(f, delimiter='	'))

ledger = read_tsv('ledger.tsv')
products = read_tsv('products.tsv')
launches = read_tsv('launches.tsv')
experiments = read_tsv('experiments.tsv')

revenue = sum(float(r['amount'] or 0) for r in ledger if r['type'] in {'sale','cash_in'})
spend = sum(float(r['amount'] or 0) for r in ledger if r['type'] in {'cash_out','refund','tool_spend','ad_spend'})
refunds = sum(float(r['amount'] or 0) for r in ledger if r['type'] == 'refund')
by_type = Counter(r['type'] for r in ledger)
visits = sum(int(r.get('clicks') or 0) for r in launches)
downloads = sum(int(r.get('downloads') or 0) for r in launches)
sales = sum(int(r.get('sales') or 0) for r in launches)

print('SUMMARY')
print(f'ledger_rows	{len(ledger)}')
print(f'products	{len(products)}')
print(f'experiments	{len(experiments)}')
print(f'gross_revenue	{revenue:.2f}')
print(f'spend	{spend:.2f}')
print(f'refunds	{refunds:.2f}')
print(f'net	{revenue - spend:.2f}')
print(f'launch_clicks	{visits}')
print(f'downloads	{downloads}')
print(f'launch_sales	{sales}')
print('events_by_type')
for key, value in sorted(by_type.items()):
    print(f'{key}	{value}')
