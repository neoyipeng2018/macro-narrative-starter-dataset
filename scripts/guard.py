#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'ledger.tsv'
PROTECTED_RESERVE = 900.0
INITIAL_CASH = 1000.0
MAX_PRE_REVENUE_OPS_SPEND = 100.0

def rows():
    with LEDGER.open(newline='') as f:
        yield from csv.DictReader(f, delimiter='	')

def main() -> int:
    cash = INITIAL_CASH
    spend = 0.0
    revenue = 0.0
    for row in rows():
        typ = row['type']
        amount = float(row['amount'] or 0)
        if typ in {'cash_out', 'refund', 'tool_spend', 'ad_spend'}:
            cash -= amount
            spend += amount
        elif typ in {'sale', 'cash_in'}:
            cash += amount
            revenue += amount
    problems = []
    if cash < PROTECTED_RESERVE:
        problems.append(f'cash ${cash:.2f} below protected reserve ${PROTECTED_RESERVE:.2f}')
    if revenue < 250 and spend > MAX_PRE_REVENUE_OPS_SPEND:
        problems.append(f'pre-revenue spend ${spend:.2f} exceeds ${MAX_PRE_REVENUE_OPS_SPEND:.2f}')
    if problems:
        print('GUARD FAIL')
        for p in problems:
            print('-', p)
        return 1
    print('GUARD PASS')
    print(f'cash_estimate	{cash:.2f}')
    print(f'revenue	{revenue:.2f}')
    print(f'spend	{spend:.2f}')
    print(f'protected_reserve	{PROTECTED_RESERVE:.2f}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
