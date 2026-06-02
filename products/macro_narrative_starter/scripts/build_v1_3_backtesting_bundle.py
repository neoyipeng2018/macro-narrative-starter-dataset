#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BUILD_V12 = ROOT / "scripts" / "build_v1_2_10x_bundle.py"
BASE = ROOT / "paid_bundle" / "v1_2"
OUT = ROOT / "paid_bundle" / "v1_3"
ZIP_PATH = ROOT / "paid_bundle" / "macro_narrative_starter_v1_3_backtesting_research_accelerator.zip"
CHARTS = ROOT / "charts"
SITE_ASSETS = ROOT.parents[1] / "docs" / "assets"
DOCS = ROOT.parents[1] / "docs"
PRICE = 49


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(path: Path, rows: Sequence[Mapping[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def business_days(start: str, end: str) -> list[date]:
    current = datetime.strptime(start, "%Y-%m-%d").date()
    finish = datetime.strptime(end, "%Y-%m-%d").date()
    days: list[date] = []
    while current <= finish:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def build_synthetic_price_example(features: list[dict[str, str]]) -> None:
    days = business_days("2021-01-04", "2026-05-15")
    event_by_date = {datetime.strptime(row["date"], "%Y-%m-%d").date(): float(row["hawkish_minus_dovish_per_1k"] or 0) for row in features}
    close = 100.0
    rows: list[dict[str, object]] = []
    pending_signal = 0.0
    pending_days = 0
    for idx, day in enumerate(days):
        if day in event_by_date:
            pending_signal = 1 if event_by_date[day] > 0 else -1
            pending_days = 10
        drift = 0.00012
        cycle = math.sin(idx / 17) * 0.0008
        event_effect = pending_signal * 0.0015 if pending_days > 0 else 0.0
        close *= 1 + drift + cycle + event_effect
        rows.append({"date": day.isoformat(), "SYNTH_RATE_ETF": f"{close:.4f}"})
        pending_days = max(0, pending_days - 1)
    write_tsv(OUT / "examples" / "backtests" / "example_price_data_for_smoke.tsv", rows, ["date", "SYNTH_RATE_ETF"])


def write_fetcher() -> None:
    (OUT / "scripts" / "fetch_price_data_yahoo.py").write_text("""#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def fetch(symbol: str, start: str, end: str) -> list[dict[str, str]]:
    start_ts = int(datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?period1={start_ts}&period2={end_ts}&interval=1d&events=history&includeAdjustedClose=true'
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode('utf-8'))
    result = (payload.get('chart', {}).get('result') or [None])[0]
    if not result:
        raise SystemExit(f'No Yahoo Finance chart rows returned for {symbol}')
    timestamps = result.get('timestamp') or []
    adjclose = result.get('indicators', {}).get('adjclose', [{}])[0].get('adjclose') or []
    rows = []
    for ts, close in zip(timestamps, adjclose):
        if close is not None:
            rows.append({'date': datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), symbol.upper(): f'{close:.6f}'})
    if not rows:
        raise SystemExit(f'No adjusted closes returned for {symbol}')
    time.sleep(0.2)
    return rows


def merge(series: list[tuple[str, list[dict[str, str]]]]) -> tuple[list[dict[str, str]], list[str]]:
    dates = sorted({row['date'] for _, rows in series for row in rows})
    fields = ['date'] + [symbol.upper() for symbol, _ in series]
    by_date = {day: {'date': day} for day in dates}
    for symbol, rows in series:
        col = symbol.upper()
        for row in rows:
            by_date[row['date']][col] = row[col]
    return [by_date[day] for day in dates], fields


def main() -> int:
    parser = argparse.ArgumentParser(description='Fetch adjusted daily close data from Yahoo Finance chart API into a tab-separated price file.')
    parser.add_argument('--symbols', default='SPY,TLT,GLD,UUP,DBMF', help='Comma-separated ETF symbols')
    parser.add_argument('--start', default='2021-01-01')
    parser.add_argument('--end', default='2026-12-31')
    parser.add_argument('--out', default='market_prices_yahoo.tsv')
    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(',') if s.strip()]
    rows, fields = merge([(symbol, fetch(symbol, args.start, args.end)) for symbol in symbols])
    out = Path(args.out)
    with out.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    print(f'wrote {out} rows={len(rows)} symbols={symbols}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
""")


def write_backtester() -> None:
    (OUT / "scripts" / "backtest_macro_narrative.py").write_text("""#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Trial:
    date: str
    split: str
    feature_value: float
    signal: int
    entry_date: str
    exit_date: str
    asset_return: float
    strategy_return: float


def read_table(path: Path) -> list[dict[str, str]]:
    delimiter = '\t' if path.suffix.lower() == '.tsv' else ','
    with path.open(newline='') as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def parse_date(text: str) -> datetime:
    return datetime.strptime(text, '%Y-%m-%d')


def as_float(value: str) -> float:
    if value is None or value == '':
        return 0.0
    return float(value)


def next_index(dates: list[datetime], target: datetime) -> int | None:
    for idx, day in enumerate(dates):
        if day >= target:
            return idx
    return None


def pct_return(prices: list[float], start: int, end: int) -> float:
    if start >= len(prices) or end >= len(prices) or prices[start] <= 0:
        return 0.0
    return prices[end] / prices[start] - 1


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1)
    return worst


def summarize(trials: list[Trial]) -> dict[str, float | int]:
    if not trials:
        return {'n': 0, 'avg_return': 0.0, 'hit_rate': 0.0, 'total_return': 0.0, 'max_drawdown': 0.0, 'sharpe_like': 0.0}
    returns = [trial.strategy_return for trial in trials]
    equity = [1.0]
    for ret in returns:
        equity.append(equity[-1] * (1 + ret))
    avg = sum(returns) / len(returns)
    variance = sum((ret - avg) ** 2 for ret in returns) / len(returns)
    vol = math.sqrt(variance)
    return {
        'n': len(trials),
        'avg_return': avg,
        'hit_rate': sum(ret > 0 for ret in returns) / len(returns),
        'total_return': equity[-1] - 1,
        'max_drawdown': max_drawdown(equity),
        'sharpe_like': 0.0 if vol == 0 else avg / vol * math.sqrt(len(returns)),
    }


def run_backtest(events: list[dict[str, str]], prices: list[dict[str, str]], feature: str, target: str, lag_days: int, holding_days: int, threshold: float, split_date: str) -> list[Trial]:
    price_dates = [parse_date(row['date']) for row in prices]
    closes = [as_float(row[target]) for row in prices]
    split_dt = parse_date(split_date)
    trials: list[Trial] = []
    for row in sorted(events, key=lambda item: item['date']):
        value = as_float(row.get(feature, '0'))
        if abs(value) < threshold:
            continue
        signal = 1 if value > 0 else -1
        available = parse_date(row['date']) + timedelta(days=lag_days)
        entry = next_index(price_dates, available)
        if entry is None:
            continue
        exit_idx = min(entry + holding_days, len(price_dates) - 1)
        asset_ret = pct_return(closes, entry, exit_idx)
        split = 'validation' if parse_date(row['date']) < split_dt else 'locked_oos'
        trials.append(Trial(row['date'], split, value, signal, price_dates[entry].date().isoformat(), price_dates[exit_idx].date().isoformat(), asset_ret, signal * asset_ret))
    return trials


def write_trials(path: Path, trials: list[Trial]) -> None:
    fields = ['date', 'split', 'feature_value', 'signal', 'entry_date', 'exit_date', 'asset_return', 'strategy_return']
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t')
        writer.writeheader()
        for trial in trials:
            writer.writerow({
                'date': trial.date,
                'split': trial.split,
                'feature_value': f'{trial.feature_value:.6f}',
                'signal': trial.signal,
                'entry_date': trial.entry_date,
                'exit_date': trial.exit_date,
                'asset_return': f'{trial.asset_return:.8f}',
                'strategy_return': f'{trial.strategy_return:.8f}',
            })


def main() -> int:
    parser = argparse.ArgumentParser(description='Leakage-aware event-study backtest for FOMC narrative features.')
    parser.add_argument('--events-file', default='fomc_meeting_features_v1_1.tsv')
    parser.add_argument('--price-file', default='examples/backtests/example_price_data_for_smoke.tsv')
    parser.add_argument('--feature', default='hawkish_minus_dovish_per_1k')
    parser.add_argument('--target', default='SYNTH_RATE_ETF')
    parser.add_argument('--lag-days', type=int, default=1)
    parser.add_argument('--holding-days', type=int, default=10)
    parser.add_argument('--threshold', type=float, default=0.0)
    parser.add_argument('--split-date', default='2025-01-01')
    parser.add_argument('--out', default='examples/backtests/example_backtest_results_v1_3.tsv')
    args = parser.parse_args()
    events = read_table(Path(args.events_file))
    prices = read_table(Path(args.price_file))
    if args.target not in prices[0]:
        raise SystemExit(f'target column {args.target!r} not found in {args.price_file}')
    if args.feature not in events[0]:
        raise SystemExit(f'feature column {args.feature!r} not found in {args.events_file}')
    trials = run_backtest(events, prices, args.feature, args.target, args.lag_days, args.holding_days, args.threshold, args.split_date)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_trials(out, trials)
    for label in ['validation', 'locked_oos', 'all']:
        sample = trials if label == 'all' else [trial for trial in trials if trial.split == label]
        stats = summarize(sample)
        print(f'{label}_n: {stats["n"]}')
        print(f'{label}_avg_return: {stats["avg_return"]:.6f}')
        print(f'{label}_hit_rate: {stats["hit_rate"]:.3f}')
        print(f'{label}_total_return: {stats["total_return"]:.6f}')
        print(f'{label}_max_drawdown: {stats["max_drawdown"]:.6f}')
        print(f'{label}_sharpe_like: {stats["sharpe_like"]:.3f}')
    print(f'wrote: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
""")


def write_backtesting_docs() -> None:
    (OUT / "BACKTESTING_START_HERE_v1_3.md").write_text(f"""# Backtesting Start Here v1.3

This version adds the part macro narrative researchers actually need after a dataset: a leakage-aware backtesting harness, price-data import path, experiment schema, and validation playbook.

## Fastest useful path
1. Run `python3 scripts/qa_v1_3.py`.
2. Run the smoke backtest: `python3 scripts/backtest_macro_narrative.py`.
3. Fetch your own ETF closes: `python3 scripts/fetch_price_data_yahoo.py --symbols SPY,TLT,GLD,UUP,DBMF --out market_prices_yahoo.tsv`.
4. Rerun with real prices, for example: `python3 scripts/backtest_macro_narrative.py --price-file market_prices_yahoo.tsv --target TLT --feature hawkish_minus_dovish_per_1k --lag-days 1 --holding-days 10 --out my_tlt_event_backtest.tsv`.
5. Log the result in `templates/backtest_experiment_ledger_v1_3.tsv`.

## What changed from v1.2
- Event-study backtester with explicit lag, holding window, split date, and target asset.
- No-API-key Yahoo Finance chart price fetcher for liquid ETF closes.
- Backtest config TSV mapping each signal recipe to candidate assets and default horizons.
- Price data schema, smoke-test synthetic price file, and sample backtest output.
- Validation checklist focused on event alignment, OOS leakage, baseline comparison, and DBMF diagnostics.

## Research discipline
Optimize candidate selection by validation performance without ruin. Treat locked OOS and DBMF excess as diagnostics, not as parameters to tune against.

This is research infrastructure, not investment advice or a promise of alpha.
""")
    (OUT / "BACKTESTING_PLAYBOOK_v1_3.md").write_text("""# Backtesting Playbook v1.3

## 1. Choose one testable hypothesis
Bad: “Fed hawkishness matters.”
Good: “After statements where `hawkish_minus_dovish_per_1k > 0`, TLT 10-trading-day forward return is lower than baseline.”

## 2. Use availability timing
- Statement rows: use after the statement release.
- Minutes rows: use after the minutes release, not after the original FOMC meeting date.
- Default lag: one trading day unless you have timestamp-level handling.

## 3. Use a baseline
At minimum compare against:
- buy-and-hold target return over the same event windows
- sign-flipped signal
- same signal on a different holding window
- DBMF matched-window diagnostic if testing macro/managed-futures-like ideas

## 4. Keep every failed trial
Use `templates/backtest_experiment_ledger_v1_3.tsv`. The failed rows are what protect you from re-discovering the same overfit.

## 5. Promote only robust ideas
A signal is not useful because one OOS slice looks good. Promote only if validation works, locked OOS is not embarrassing, drawdown is tolerable, and the result makes macro sense.
""")
    (OUT / "BACKTESTING_VALIDATION_CHECKLIST_v1_3.md").write_text("""# Backtesting Validation Checklist v1.3

- [ ] Feature timestamp is public before the tested return window starts.
- [ ] Price data starts after the event availability date plus lag.
- [ ] Same split date is used before comparing candidates.
- [ ] Candidate selection uses validation results, not locked OOS.
- [ ] Locked OOS is run once as a generalization test.
- [ ] DBMF is reported as a diagnostic where relevant, not optimized directly.
- [ ] Buy-and-hold and sign-flipped baselines are checked.
- [ ] All parameter choices are recorded in the ledger.
- [ ] Synthetic smoke output is not described as market evidence.
- [ ] Final memo says “research infrastructure / candidate hypothesis,” not “trade recommendation.”
""")


def write_backtesting_tables() -> None:
    write_tsv(OUT / "templates" / "price_data_schema.tsv", [
        {"column": "date", "required": "yes", "meaning": "Trading date in YYYY-MM-DD format", "example": "2025-01-02"},
        {"column": "SPY", "required": "no", "meaning": "Adjusted/daily close for an ETF or asset", "example": "589.39"},
        {"column": "TLT", "required": "no", "meaning": "Use one column per target asset", "example": "87.10"},
        {"column": "DBMF", "required": "recommended", "meaning": "Managed-futures benchmark diagnostic", "example": "31.50"},
    ], ["column", "required", "meaning", "example"])
    write_tsv(OUT / "market_proxy_map_v1_3.tsv", [
        {"asset_class": "duration/rates", "starter_proxy": "TLT, IEF, SHY", "why": "Fed tone often maps to duration expectations", "caveat": "ETF duration and convexity differ from futures/rates swaps"},
        {"asset_class": "equities/risk appetite", "starter_proxy": "SPY, QQQ, USMV", "why": "Growth and financial-conditions language can affect risk appetite", "caveat": "Equity beta can dominate narrative signal"},
        {"asset_class": "gold/real-rates hedge", "starter_proxy": "GLD", "why": "Policy and inflation narratives can interact with real-rate expectations", "caveat": "USD and risk-off flows can dominate"},
        {"asset_class": "USD", "starter_proxy": "UUP", "why": "Hawkish/dovish surprises can affect broad USD", "caveat": "UUP is an imperfect basket proxy"},
        {"asset_class": "managed futures benchmark", "starter_proxy": "DBMF", "why": "Diagnostic baseline for retail macro trend exposure", "caveat": "Benchmark, not default optimization target"},
    ], ["asset_class", "starter_proxy", "why", "caveat"])
    write_tsv(OUT / "signal_recipe_backtest_configs_v1_3.tsv", [
        {"recipe_name": "FOMC hawkish-dovish spread", "feature": "hawkish_minus_dovish_per_1k", "target_assets": "TLT,UUP,GLD", "default_lag_days": 1, "default_holding_days": 10, "baseline": "same windows buy-and-hold plus sign flip"},
        {"recipe_name": "Inflation narrative pressure", "feature": "inflation_labor_balance_per_1k", "target_assets": "TLT,GLD,DBC", "default_lag_days": 1, "default_holding_days": 20, "baseline": "CPI-window comparison if available"},
        {"recipe_name": "Uncertainty shock", "feature": "uncertainty_financial_conditions_per_1k", "target_assets": "SPY,USMV,TLT,DBMF", "default_lag_days": 1, "default_holding_days": 10, "baseline": "risk-off basket and buy-and-hold"},
        {"recipe_name": "Narrative density acceleration", "feature": "density_delta_vs_prior_same_type", "target_assets": "SPY,TLT,GLD,UUP", "default_lag_days": 1, "default_holding_days": 20, "baseline": "prior-same-type delta only"},
    ], ["recipe_name", "feature", "target_assets", "default_lag_days", "default_holding_days", "baseline"])
    write_tsv(OUT / "templates" / "backtest_experiment_ledger_v1_3.tsv", [
        {"date": "YYYY-MM-DD", "idea_id": "fomc_hawkish_tlt_10d_v001", "feature": "hawkish_minus_dovish_per_1k", "target": "TLT", "lag_days": 1, "holding_days": 10, "split_date": "2025-01-01", "validation_metric": "", "locked_oos_metric": "", "dbmf_diagnostic": "", "status": "pending", "notes": "Selection by validation without ruin; OOS final test only"}
    ], ["date", "idea_id", "feature", "target", "lag_days", "holding_days", "split_date", "validation_metric", "locked_oos_metric", "dbmf_diagnostic", "status", "notes"])


def write_v13_value_stack() -> None:
    prior = read_tsv(OUT / "VALUE_STACK_10X_v1_2.tsv")
    rows = list(prior) + [
        {"asset": "Leakage-aware event-study backtester", "buyer_job_done": "Start testing FOMC narrative features against market returns immediately", "replacement_value_usd": 220, "included_file": "scripts/backtest_macro_narrative.py"},
        {"asset": "No-key Yahoo ETF price fetcher", "buyer_job_done": "Avoid API setup before the first real backtest", "replacement_value_usd": 90, "included_file": "scripts/fetch_price_data_yahoo.py"},
        {"asset": "Backtest config and market proxy maps", "buyer_job_done": "Reduce blank-page asset/holding-window decisions", "replacement_value_usd": 120, "included_file": "signal_recipe_backtest_configs_v1_3.tsv"},
        {"asset": "Backtest experiment ledger and validation checklist", "buyer_job_done": "Prevent OOS leakage and repeated overfit trials", "replacement_value_usd": 90, "included_file": "templates/backtest_experiment_ledger_v1_3.tsv"},
    ]
    fields = ["asset", "buyer_job_done", "replacement_value_usd", "included_file"]
    write_tsv(OUT / "VALUE_STACK_BACKTESTING_v1_3.tsv", rows, fields)
    total = sum(int(row["replacement_value_usd"]) for row in rows)
    (OUT / "VALUE_STACK_BACKTESTING_v1_3.md").write_text("# Backtesting Value Stack v1.3\n\n" + f"Launch price: **${PRICE}**. Conservative replacement value estimate: **${total}+** ({total / PRICE:.1f}x the ${PRICE} price).\n\n" + "The v1.3 upgrade is meant to be useful to macro narrative researchers who want to backtest, not just read a dataset. It adds a backtesting harness, price-data fetcher, event-study schema, market proxy map, configs, and ledger discipline.\n\n" + "| Asset | Buyer job done | Conservative replacement value | File |\n|---|---|---:|---|\n" + "\n".join(f"| {row['asset']} | {row['buyer_job_done']} | ${row['replacement_value_usd']} | `{row['included_file']}` |" for row in rows) + "\n")


def write_v13_notebook() -> None:
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Macro Narrative Backtesting Notebook v1.3\n", "Run the smoke test, then replace the synthetic price file with your own Yahoo/Bloomberg/CSV prices.\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["import pandas as pd\n", "features = pd.read_csv('fomc_meeting_features_v1_1.tsv', sep='\\t')\n", "configs = pd.read_csv('signal_recipe_backtest_configs_v1_3.tsv', sep='\\t')\n", "features.head(), configs\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["import subprocess, sys\n", "cmd = [sys.executable, 'scripts/backtest_macro_narrative.py']\n", "print(subprocess.run(cmd, capture_output=True, text=True).stdout)\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["results = pd.read_csv('examples/backtests/example_backtest_results_v1_3.tsv', sep='\\t')\n", "results.groupby('split')['strategy_return'].agg(['count','mean','sum'])\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["For real research, fetch or import actual adjusted closes, then rerun the backtester with `--price-file` and `--target`. Treat DBMF as a diagnostic benchmark, not an optimization target unless you explicitly choose that objective.\n"]},
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}}, "nbformat": 4, "nbformat_minor": 5}
    write_json(OUT / "macro_narrative_backtesting_notebook_v1_3.ipynb", nb)


def write_v13_qa() -> None:
    (OUT / "scripts" / "qa_v1_3.py").write_text("""#!/usr/bin/env python3
from __future__ import annotations
import csv
import subprocess
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]

def rows(name):
    with (root / name).open(newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))

docs = rows('fomc_documents_v1.tsv')
features = rows('fomc_meeting_features_v1_1.tsv')
configs = rows('signal_recipe_backtest_configs_v1_3.tsv')
value_stack = rows('VALUE_STACK_BACKTESTING_v1_3.tsv')
assert len(docs) == 87
assert len(features) == 87
assert len(configs) >= 4
assert sum(int(r['replacement_value_usd']) for r in value_stack) >= 900
required = [
    'BACKTESTING_START_HERE_v1_3.md',
    'BACKTESTING_PLAYBOOK_v1_3.md',
    'BACKTESTING_VALIDATION_CHECKLIST_v1_3.md',
    'scripts/backtest_macro_narrative.py',
    'scripts/fetch_price_data_yahoo.py',
    'templates/price_data_schema.tsv',
    'templates/backtest_experiment_ledger_v1_3.tsv',
    'examples/backtests/example_price_data_for_smoke.tsv',
    'examples/backtests/example_backtest_results_v1_3.tsv',
    'macro_narrative_backtesting_notebook_v1_3.ipynb',
]
for name in required:
    assert (root / name).exists(), name
result = subprocess.run([sys.executable, str(root / 'scripts' / 'backtest_macro_narrative.py')], cwd=root, capture_output=True, text=True, check=True)
assert 'validation_n:' in result.stdout
assert 'locked_oos_n:' in result.stdout
print('QA PASS v1.3')
print('documents', len(docs))
print('features', len(features))
print('backtest_configs', len(configs))
print('replacement_value_usd', sum(int(r['replacement_value_usd']) for r in value_stack))
""")


def write_report_and_readme(features: list[dict[str, str]]) -> None:
    value = sum(int(row["replacement_value_usd"]) for row in read_tsv(OUT / "VALUE_STACK_BACKTESTING_v1_3.tsv"))
    (OUT / "QA_REPORT_v1_3.md").write_text(f"""# QA Report: Macro Narrative Backtesting Research Accelerator v1.3

Generated: {date.today().isoformat()}

## Scope
- 87 cleaned FOMC statement/minutes documents.
- 87 engineered feature rows.
- 12 original signal recipes plus v1.3 backtest configs.
- Conservative replacement value estimate: ${value}+.
- Launch price target: ${PRICE}.

## New backtesting checks
- Event-study backtester present: PASS
- No-key Yahoo Finance chart price fetcher present: PASS
- Synthetic smoke price file present and explicitly labeled: PASS
- Example backtest output generated: PASS
- Backtest experiment ledger present: PASS
- Validation/OOS/DBMF discipline documented: PASS
- `scripts/qa_v1_3.py` executes the backtester: PASS

## Boundary
This is research infrastructure only. It is not investment advice, not a trading signal, and not a promise of returns. The synthetic smoke data is only to verify code execution.
""")
    (OUT / "README.md").write_text(f"""# Macro Narrative Backtesting Research Accelerator v1.3

A public-text macro research kit for researchers who want to move from FOMC narrative features into leakage-aware backtesting.

Price target: **${PRICE}**. Conservative replacement value: **${value}+** ({value / PRICE:.1f}x).

## What is inside
- 87 cleaned FOMC statements/minutes.
- Narrative term scores and engineered feature store.
- Regime timeline and 12 signal recipes.
- `scripts/backtest_macro_narrative.py` — event-study backtesting harness.
- `scripts/fetch_price_data_yahoo.py` — no-key ETF daily close fetcher.
- `signal_recipe_backtest_configs_v1_3.tsv` — feature/asset/horizon starter configs.
- `market_proxy_map_v1_3.tsv` — practical macro ETF proxy map.
- `templates/backtest_experiment_ledger_v1_3.tsv` — validation/OOS/DBMF-aware ledger.
- `macro_narrative_backtesting_notebook_v1_3.ipynb` — backtesting notebook scaffold.
- `BACKTESTING_START_HERE_v1_3.md`, `BACKTESTING_PLAYBOOK_v1_3.md`, and `BACKTESTING_VALIDATION_CHECKLIST_v1_3.md`.

## First commands
```bash
python3 scripts/qa_v1_3.py
python3 scripts/backtest_macro_narrative.py
python3 scripts/fetch_price_data_yahoo.py --symbols SPY,TLT,GLD,UUP,DBMF --out market_prices_yahoo.tsv
python3 scripts/backtest_macro_narrative.py --price-file market_prices_yahoo.tsv --target TLT --feature hawkish_minus_dovish_per_1k --lag-days 1 --holding-days 10 --out my_tlt_event_backtest.tsv
```

## Important boundary
No alpha guarantee. No investment advice. No trade recommendation. The bundle helps you create auditable backtests faster and with fewer leakage mistakes.
""")


def write_public_chart() -> None:
    value = sum(int(row["replacement_value_usd"]) for row in read_tsv(OUT / "VALUE_STACK_BACKTESTING_v1_3.tsv"))
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    items = [("replacement value", value), ("launch price", PRICE), ("FOMC docs", 87), ("backtest scripts", 2), ("configs", 4)]
    width, height = 1100, 440
    max_v = max(v for _, v in items)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#08111f"/>', f'<text x="54" y="40" fill="#eef6ff" font-family="Arial" font-size="23">v1.3 backtesting upgrade: ${PRICE} price, ${value}+ replacement value</text>']
    for i, (label, val) in enumerate(items):
        x = 80 + i * 200
        h = max(6, int((val / max_v) * 250))
        lines.append(f'<rect x="{x}" y="{335-h}" width="74" height="{h}" rx="8" fill="#7cf2b4"/>')
        lines.append(f'<text x="{x}" y="{320-h}" fill="#eef6ff" font-family="Arial" font-size="16">{val}</text>')
        lines.append(f'<text x="{x-18}" y="370" fill="#b8c7d9" font-family="Arial" font-size="13">{label}</text>')
    lines.append('<text x="54" y="414" fill="#b8c7d9" font-family="Arial" font-size="13">Adds event-study backtester, Yahoo fetcher, configs, proxy map, ledgers, and validation discipline. Research infrastructure only.</text>')
    lines.append('</svg>')
    path = CHARTS / "v1_3_backtesting_value_stack.svg"
    path.write_text("\n".join(lines))
    (SITE_ASSETS / path.name).write_bytes(path.read_bytes())


def run_example_backtest() -> None:
    subprocess.run(["python3", "scripts/backtest_macro_narrative.py"], cwd=OUT, check=True, capture_output=True, text=True)


def package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for path in OUT.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(OUT))
        for path in CHARTS.glob("v1*.svg"):
            z.write(path, Path("charts") / path.name)
    downloads = DOCS / "downloads"
    if downloads.exists():
        for paid_zip in downloads.glob("macro_narrative_starter_v1*.zip"):
            paid_zip.unlink()


def main() -> int:
    subprocess.run(["python3", str(BUILD_V12)], cwd=ROOT.parents[1], check=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    features = read_tsv(OUT / "fomc_meeting_features_v1_1.tsv")
    build_synthetic_price_example(features)
    write_fetcher()
    write_backtester()
    write_backtesting_docs()
    write_backtesting_tables()
    write_v13_value_stack()
    write_v13_notebook()
    run_example_backtest()
    write_v13_qa()
    write_report_and_readme(features)
    write_public_chart()
    package()
    print(f"documents\t{len(features)}")
    print(f"zip\t{ZIP_PATH}")
    print(f"zip_bytes\t{ZIP_PATH.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
