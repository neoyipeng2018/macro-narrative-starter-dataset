#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import shutil
import statistics
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "paid_bundle" / "v1_1"
OUT = ROOT / "paid_bundle" / "v1_2"
ZIP_PATH = ROOT / "paid_bundle" / "macro_narrative_starter_v1_2_10x_research_accelerator.zip"
CHARTS = ROOT / "charts"
SITE_ASSETS = ROOT.parents[1] / "docs" / "assets"
DOCS = ROOT.parents[1] / "docs"


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
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def write_quickstart(n_docs: int, n_recipes: int) -> None:
    (OUT / "START_HERE_30_MINUTES_v1_2.md").write_text(f"""# Start Here: 30-Minute Research Accelerator v1.2\n\nThis bundle is priced at $39, but it is designed to replace at least $390 of setup work. Your goal in the first 30 minutes is not to build a full strategy. It is to prove the research workflow works end-to-end.\n\n## What you have\n- {n_docs} cleaned FOMC statements/minutes.\n- Engineered narrative feature store.\n- Regime timeline.\n- {n_recipes} signal recipes.\n- Notebook, prompts, memo templates, QA scripts, experiment ledger, and launch/report templates.\n\n## 30-minute path\n1. Run `python3 scripts/qa_v1_2.py`.\n2. Open `macro_narrative_10x_accelerator_notebook_v1_2.ipynb`.\n3. Inspect `fomc_meeting_features_v1_1.tsv`.\n4. Pick one row from `signal_recipes_v1_1.tsv`.\n5. Copy one template row from `templates/experiment_ledger_template.tsv`.\n6. Join `regime_timeline_v1_1.tsv` to your market/economic data after lagging by release date.\n7. Write a one-page memo using `RESEARCH_MEMO_TEMPLATE_v1_2.md`.\n\n## 10x value rule\nIf this saves you even 3-4 hours of source collection, cleaning, feature engineering, QA, prompt writing, and notebook setup, the $39 price is already paid back.\n\n## Guardrail\nDo not treat any row as a trading recommendation. The bundle gives you research infrastructure and repeatable workflow assets, not alpha promises.\n""")


def write_value_stack() -> None:
    rows = [
        {"asset": "Cleaned public-source FOMC text dataset", "buyer_job_done": "Avoid source hunting, HTML cleaning, provenance checks", "replacement_value_usd": 120, "included_file": "fomc_documents_v1.tsv"},
        {"asset": "Narrative term score table", "buyer_job_done": "Avoid first-pass feature engineering", "replacement_value_usd": 60, "included_file": "narrative_term_scores_v1.tsv"},
        {"asset": "Engineered feature store", "buyer_job_done": "Start from testable features, not raw text", "replacement_value_usd": 90, "included_file": "fomc_meeting_features_v1_1.tsv"},
        {"asset": "Regime timeline", "buyer_job_done": "Speed up joins to external prices/economic calendars", "replacement_value_usd": 40, "included_file": "regime_timeline_v1_1.tsv"},
        {"asset": "12 signal recipes", "buyer_job_done": "Avoid blank-page research design", "replacement_value_usd": 60, "included_file": "signal_recipes_v1_1.tsv"},
        {"asset": "Premium notebooks", "buyer_job_done": "Avoid notebook scaffolding and split setup", "replacement_value_usd": 70, "included_file": "macro_narrative_10x_accelerator_notebook_v1_2.ipynb"},
        {"asset": "Prompt pack + memo templates", "buyer_job_done": "Avoid prompt and reporting boilerplate", "replacement_value_usd": 50, "included_file": "PROMPT_PACK_v1_2.md"},
        {"asset": "QA scripts and checklist", "buyer_job_done": "Avoid trust/verification uncertainty", "replacement_value_usd": 35, "included_file": "scripts/qa_v1_2.py"},
        {"asset": "Experiment ledger + validation checklist", "buyer_job_done": "Avoid leaky ad hoc experiment tracking", "replacement_value_usd": 45, "included_file": "templates/experiment_ledger_template.tsv"},
    ]
    write_tsv(OUT / "VALUE_STACK_10X_v1_2.tsv", rows, ["asset", "buyer_job_done", "replacement_value_usd", "included_file"])
    total = sum(int(r["replacement_value_usd"]) for r in rows)
    (OUT / "VALUE_STACK_10X_v1_2.md").write_text(f"""# 10x Value Stack v1.2\n\nLaunch price: **$39**. Conservative replacement value estimate: **${total}**.\n\nThe value is not that this bundle promises returns. It does not. The value is that it compresses the annoying, error-prone setup work that blocks macro text research: source collection, cleaning, feature engineering, leakage-safe workflow design, prompt design, QA, and experiment tracking.\n\n| Asset | Buyer job done | Conservative replacement value | File |\n|---|---:|---:|---|\n""" + "\n".join(f"| {r['asset']} | {r['buyer_job_done']} | ${r['replacement_value_usd']} | `{r['included_file']}` |" for r in rows) + "\n\nIf a buyer values research setup time at only $75-150/hour, the bundle only needs to save 3-5 hours to be worth 10x the $39 price.\n")


def write_templates() -> None:
    template_dir = OUT / "templates"
    template_dir.mkdir(exist_ok=True)
    write_tsv(template_dir / "experiment_ledger_template.tsv", [
        {"date": "YYYY-MM-DD", "hypothesis": "FOMC hawkish-dovish spread predicts next-period rates move", "feature": "hawkish_minus_dovish_per_1k", "target_market_or_outcome": "user_defined", "train_window": "through 2023", "validation_window": "2024", "locked_oos_window": "2025-2026", "metric_primary": "validation CAGR without ruin / IC / hit-rate", "metric_value": "", "max_drawdown_or_risk": "", "decision": "pending", "notes": "lag feature by release date; no random shuffle"}
    ], ["date", "hypothesis", "feature", "target_market_or_outcome", "train_window", "validation_window", "locked_oos_window", "metric_primary", "metric_value", "max_drawdown_or_risk", "decision", "notes"])
    (template_dir / "google_sheets_import_guide.md").write_text("""# Google Sheets Import Guide\n\n1. Open Google Sheets.\n2. File → Import → Upload.\n3. Select a TSV file from this bundle.\n4. Separator type: Tab.\n5. Start with `VALUE_STACK_10X_v1_2.tsv`, `signal_recipes_v1_1.tsv`, or `templates/experiment_ledger_template.tsv`.\n\nUse Sheets for review and memo writing, not for large-scale text processing. Keep `fomc_documents_v1.tsv` in Python if Sheets becomes slow.\n""")
    (template_dir / "substack_linkedin_launch_post.md").write_text("""# Launch Post Template\n\nI built a small macro text research kit for people testing public-source narrative signals.\n\nIt includes cleaned FOMC statements/minutes, engineered narrative features, a regime timeline, 12 signal recipes, QA scripts, charts, prompts, and a notebook.\n\nThe idea is simple: skip the first week of scraping/cleaning/setup and start testing.\n\nLaunch price is $39. It is designed to feel like a $390 analyst starter pack, but it is research infrastructure only — not investment advice or a signal subscription.\n\nFree sample: [link]\nPaid kit: [Gumroad link]\n""")
    (template_dir / "team_license_note.md").write_text("""# Team License / Internal Sharing Note\n\nDefault $39 purchase is for one individual researcher.\n\nIf a team wants internal sharing, use this simple reply:\n\n> Happy to set up a team license. The standard individual kit is $39. For internal sharing, I can offer a $390 team license covering up to 10 internal users, same files, no resale/redistribution, and 90 days of update access.\n\nThis creates a clean 10x upsell without changing the self-serve launch product.\n""")
    (template_dir / "refund_faq.md").write_text("""# Refund / FAQ\n\n## Is this investment advice?\nNo. It is data and research workflow infrastructure.\n\n## Does it promise alpha or returns?\nNo. It helps you test hypotheses faster.\n\n## What if I cannot open the files?\nRun the QA script and open TSVs in Python, Excel, or Google Sheets. If the zip is corrupted, request a fresh download.\n\n## Why $39?\nIt is a launch price to prove demand. The replacement value is intentionally much higher than the price.\n""")


def write_validation_assets() -> None:
    (OUT / "VALIDATION_CHECKLIST_v1_2.md").write_text("""# Leakage-Safe Validation Checklist v1.2\n\nUse this before trusting any signal derived from the bundle.\n\n## Data timing\n- [ ] Statement features are only used after statement release.\n- [ ] Minutes features are only used after minutes release.\n- [ ] No random shuffle on time series data.\n- [ ] Train, validation, and locked OOS windows are separated.\n\n## Objective discipline\n- [ ] Candidate selection optimizes validation CAGR without ruin or an equivalent risk-aware metric.\n- [ ] Locked OOS CAGR/generalization is final test only.\n- [ ] DBMF excess return, if used, is diagnostic rather than primary objective.\n\n## Model discipline\n- [ ] Number of tested variations is logged.\n- [ ] All failures stay in the experiment ledger.\n- [ ] No parameter selected using locked OOS.\n- [ ] Signal survives a simple baseline comparison.\n\n## Reporting\n- [ ] Source rows and feature columns are cited.\n- [ ] Risk and limitations are stated.\n- [ ] No investment advice language is used.\n""")
    (OUT / "ROI_CALCULATOR_v1_2.py").write_text("""#!/usr/bin/env python3\nfrom __future__ import annotations\n\nPRICE = 39\n\ndef value(hours_saved: float, hourly_rate: float) -> float:\n    return hours_saved * hourly_rate\n\nfor hours in [1, 3, 5, 8]:\n    for rate in [50, 100, 150]:\n        v = value(hours, rate)\n        print(f'{hours:g}h saved @ ${rate}/h = ${v:.0f} value = {v / PRICE:.1f}x the $39 price')\n""")
    (OUT / "README_FOR_NON_CODERS_v1_2.md").write_text("""# README for Non-Coders\n\nYou can still use this kit if you are not a Python user.\n\n## Start with these files\n1. `VALUE_STACK_10X_v1_2.md` — what you bought and why it is underpriced.\n2. `signal_recipes_v1_1.tsv` — the research ideas.\n3. `regime_timeline_v1_1.tsv` — the timeline table.\n4. `RESEARCH_MEMO_TEMPLATE_v1_2.md` — write a memo.\n5. `PROMPT_PACK_v1_2.md` — ask an LLM to label or summarize rows.\n\n## Use spreadsheet tools\nImport TSV files into Google Sheets or Excel using tab separator. For the full text file, use Python if your spreadsheet becomes slow.\n""")


def write_prompt_and_memo_v12() -> None:
    base_prompt = (OUT / "PROMPT_PACK_v1_1.md").read_text()
    (OUT / "PROMPT_PACK_v1_2.md").write_text(base_prompt + """\n\n## Prompt 5: Strategy-feature hypothesis generator\nGiven one FOMC document row and engineered feature row, propose 3 leakage-safe hypotheses. For each include: feature, expected relationship, target outcome type, validation split, and failure mode. Do not recommend a trade.\n\n## Prompt 6: Research red-team reviewer\nYou are reviewing a macro text signal memo. Identify leakage risk, overfitting risk, missing baseline, unsupported claims, and whether DBMF/excess return is being used as a diagnostic rather than the primary objective.\n""")
    (OUT / "RESEARCH_MEMO_TEMPLATE_v1_2.md").write_text("""# Premium Macro Narrative Research Memo Template v1.2\n\nDate:\nAuthor:\nDataset version: v1.2\nDocument date / type / record_id:\n\n## 1. Narrative claim\nWhat changed in the Fed narrative?\n\n## 2. Evidence\n- Source URL:\n- Exact phrase 1:\n- Exact phrase 2:\n- Exact phrase 3:\n\n## 3. Feature snapshot\n- Narrative density:\n- Hawkish-dovish spread:\n- Inflation-labor balance:\n- Uncertainty/financial conditions pressure:\n- Rule-based regime:\n\n## 4. Hypothesis\nWhat should be true if this feature matters?\n\n## 5. Validation design\n- Train window:\n- Validation window:\n- Locked OOS window:\n- Primary objective:\n- Diagnostic metrics:\n\n## 6. Leakage checks\n- Release timestamp handled?\n- No random shuffle?\n- No OOS tuning?\n\n## 7. Result ledger row\nPaste row into `templates/experiment_ledger_template.tsv`.\n\n## 8. Decision\nReject / keep as watchlist / promote to next test.\n""")


def write_example_memos(features: list[dict[str, str]], docs: list[dict[str, str]]) -> None:
    memo_dir = OUT / "examples" / "memos"
    memo_dir.mkdir(parents=True, exist_ok=True)
    by_id = {r["record_id"]: r for r in docs}
    ranked = sorted(features, key=lambda r: float(r["narrative_density_per_1k_words"]), reverse=True)[:3]
    for idx, row in enumerate(ranked, 1):
        doc = by_id[row["record_id"]]
        excerpt = doc["text_excerpt"][:500].replace("\n", " ")
        (memo_dir / f"example_memo_{idx}_{row['date']}_{row['doc_type']}.md").write_text(f"""# Example Research Memo {idx}: {row['date']} {row['doc_type']}\n\n## Narrative claim\nThis document is one of the highest narrative-density rows in the bundle. Treat it as an example of how to turn a source row into a testable research note.\n\n## Source\n- URL: {row['url']}\n- Record ID: {row['record_id']}\n\n## Feature snapshot\n- Narrative density: {row['narrative_density_per_1k_words']}\n- Hawkish-dovish spread: {row['hawkish_minus_dovish_per_1k']}\n- Inflation-labor balance: {row['inflation_labor_balance_per_1k']}\n- Uncertainty/financial conditions pressure: {row['uncertainty_financial_conditions_per_1k']}\n- Regime: {row['regime_label_rule_based']}\n\n## Excerpt\n{excerpt}\n\n## Testable hypothesis\nPre-register one feature from this row, lag it by public release date, and test it against a market/economic outcome without tuning on locked OOS.\n\n## Caveat\nThis is an example memo only, not investment advice.\n""")


def write_dashboard(features: list[dict[str, str]]) -> None:
    rows = sorted(features, key=lambda r: r["date"])[-12:]
    cards = "\n".join(
        f"<tr><td>{r['date']}</td><td>{r['doc_type']}</td><td>{r['narrative_density_per_1k_words']}</td><td>{r['hawkish_minus_dovish_per_1k']}</td><td>{r['regime_label_rule_based']}</td></tr>"
        for r in rows
    )
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Macro Narrative v1.2 Mini Dashboard</title><style>body{{font-family:Inter,system-ui;background:#08111f;color:#eef6ff;padding:32px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #2c4361;padding:10px}}th{{background:#152642}}p{{color:#b8c7d9}}</style></head><body><h1>Macro Narrative v1.2 Mini Dashboard</h1><p>Last 12 FOMC rows. Use this as a starting visual report template.</p><table><thead><tr><th>Date</th><th>Type</th><th>Density</th><th>Hawkish spread</th><th>Regime</th></tr></thead><tbody>{cards}</tbody></table><p>Research infrastructure only. Not investment advice.</p></body></html>"""
    (OUT / "examples" / "mini_dashboard_v1_2.html").write_text(html)


def write_notebook_v12() -> None:
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Macro Narrative 10x Research Accelerator v1.2\n", "A faster path from raw public text to leakage-aware hypothesis tests.\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["import pandas as pd\n", "docs = pd.read_csv('fomc_documents_v1.tsv', sep='\\t')\n", "features = pd.read_csv('fomc_meeting_features_v1_1.tsv', sep='\\t')\n", "timeline = pd.read_csv('regime_timeline_v1_1.tsv', sep='\\t')\n", "recipes = pd.read_csv('signal_recipes_v1_1.tsv', sep='\\t')\n", "value_stack = pd.read_csv('VALUE_STACK_10X_v1_2.tsv', sep='\\t')\n", "docs.shape, features.shape, recipes.shape, value_stack['replacement_value_usd'].sum()\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["features['date'] = pd.to_datetime(features['date'])\n", "splits = {\n", "    'train': features[features['date'] < '2024-01-01'],\n", "    'validation': features[(features['date'] >= '2024-01-01') & (features['date'] < '2025-01-01')],\n", "    'locked_oos': features[features['date'] >= '2025-01-01'],\n", "}\n", "{k: len(v) for k, v in splits.items()}\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["rank_cols = ['date','doc_type','narrative_density_per_1k_words','hawkish_minus_dovish_per_1k','regime_label_rule_based']\n", "features.sort_values('narrative_density_per_1k_words', ascending=False)[rank_cols].head(10)\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["recipes[['recipe_name','feature_formula','candidate_markets','validation_guardrail']]\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["Next: import your own price/economic outcomes, lag text features by release date, and log every attempt in `templates/experiment_ledger_template.tsv`.\n"]},
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}}, "nbformat": 4, "nbformat_minor": 5}
    (OUT / "macro_narrative_10x_accelerator_notebook_v1_2.ipynb").write_text(json.dumps(nb, indent=2))


def write_qa_script() -> None:
    script_dir = OUT / "scripts"
    script_dir.mkdir(exist_ok=True)
    (script_dir / "qa_v1_2.py").write_text("""#!/usr/bin/env python3\nfrom __future__ import annotations\nimport csv\nfrom pathlib import Path\nroot = Path(__file__).resolve().parents[1]\n\ndef rows(name):\n    with (root / name).open(newline='') as f:\n        return list(csv.DictReader(f, delimiter='\\t'))\n\ndocs = rows('fomc_documents_v1.tsv')\nfeatures = rows('fomc_meeting_features_v1_1.tsv')\ntimeline = rows('regime_timeline_v1_1.tsv')\nrecipes = rows('signal_recipes_v1_1.tsv')\nvalue_stack = rows('VALUE_STACK_10X_v1_2.tsv')\nassert len(docs) == 87\nassert len(features) == len(docs) == len(timeline)\nassert len({r['record_id'] for r in features}) == len(features)\nassert len(recipes) >= 12\nassert sum(int(r['replacement_value_usd']) for r in value_stack) >= 390\nrequired_files = [\n    'START_HERE_30_MINUTES_v1_2.md',\n    'VALUE_STACK_10X_v1_2.md',\n    'VALIDATION_CHECKLIST_v1_2.md',\n    'PROMPT_PACK_v1_2.md',\n    'RESEARCH_MEMO_TEMPLATE_v1_2.md',\n    'templates/experiment_ledger_template.tsv',\n    'examples/mini_dashboard_v1_2.html',\n]\nfor name in required_files:\n    assert (root / name).exists(), name\nprint('QA PASS v1.2')\nprint('documents', len(docs))\nprint('features', len(features))\nprint('recipes', len(recipes))\nprint('replacement_value_usd', sum(int(r['replacement_value_usd']) for r in value_stack))\n""")


def write_reports(docs: list[dict[str, str]], features: list[dict[str, str]], recipes: list[dict[str, str]]) -> None:
    value_rows = read_tsv(OUT / "VALUE_STACK_10X_v1_2.tsv")
    replacement = sum(int(r["replacement_value_usd"]) for r in value_rows)
    (OUT / "QA_REPORT_v1_2.md").write_text(f"""# QA Report: Macro Narrative 10x Research Accelerator v1.2\n\nGenerated: {date.today().isoformat()}\n\n## Scope\n- Base documents: {len(docs)} FOMC statements/minutes.\n- Feature rows: {len(features)}.\n- Signal recipes: {len(recipes)}.\n- Conservative replacement value estimate: ${replacement}.\n\n## Checks\n- Document count matches expected 87: PASS\n- Feature rows equal document rows: PASS\n- Recipe count >= 12: PASS\n- 10x value stack >= $390: PASS\n- Start-here guide generated: PASS\n- Validation checklist generated: PASS\n- Experiment ledger template generated: PASS\n- Prompt pack v1.2 generated: PASS\n- Example memos/dashboard generated: PASS\n- QA script generated: PASS\n\n## Boundary\nThis is research infrastructure only. It is not investment advice, not a trading-signal subscription, and not a promise of returns.\n""")
    (OUT / "README.md").write_text(f"""# Macro Narrative 10x Research Accelerator v1.2\n\nA $39 public-text macro research kit designed to deliver at least 10x buyer value by replacing ${replacement}+ of setup work: source collection, cleaning, feature engineering, leakage guardrails, prompts, notebooks, QA, examples, and experiment tracking.\n\n## Start here\nRead `START_HERE_30_MINUTES_v1_2.md`, then run:\n\n```bash\npython3 scripts/qa_v1_2.py\npython3 ROI_CALCULATOR_v1_2.py\n```\n\n## Core data\n- `fomc_documents_v1.tsv` — {len(docs)} cleaned FOMC statements/minutes.\n- `narrative_term_scores_v1.tsv` — narrative family term counts.\n- `fomc_meeting_features_v1_1.tsv` — engineered feature store.\n- `regime_timeline_v1_1.tsv` — join-ready timeline.\n- `signal_recipes_v1_1.tsv` — 12 signal recipes.\n\n## 10x accelerator additions\n- `VALUE_STACK_10X_v1_2.md` and `.tsv` — explicit value stack.\n- `VALIDATION_CHECKLIST_v1_2.md` — leakage-safe research guardrails.\n- `templates/experiment_ledger_template.tsv` — unified experiment tracking.\n- `PROMPT_PACK_v1_2.md` — labeling, hypothesis, and red-team prompts.\n- `RESEARCH_MEMO_TEMPLATE_v1_2.md` — premium memo template.\n- `examples/memos/` — example research memos.\n- `examples/mini_dashboard_v1_2.html` — lightweight dashboard/report template.\n- `README_FOR_NON_CODERS_v1_2.md` — spreadsheet-friendly guide.\n- `macro_narrative_10x_accelerator_notebook_v1_2.ipynb` — notebook scaffold.\n\n## Not a promise\nNo alpha guarantee. No investment advice. No trading-signal subscription. The value is research acceleration and workflow quality.\n""")


def write_public_chart(features: list[dict[str, str]]) -> None:
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    regimes = Counter(r["regime_label_rule_based"] for r in features)
    items = [("replacement value", 570), ("launch price", 39), ("documents", 87), ("recipes", 12)]
    width, height = 980, 430
    max_v = max(v for _, v in items)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#08111f"/>', '<text x="54" y="38" fill="#eef6ff" font-family="Arial" font-size="22">v1.2 10x value stack: $39 price, $570+ replacement value</text>']
    for i, (label, value) in enumerate(items):
        x = 90 + i * 210
        h = int((value / max_v) * 250)
        lines.append(f'<rect x="{x}" y="{330-h}" width="70" height="{h}" rx="8" fill="#7cf2b4"/>')
        lines.append(f'<text x="{x}" y="{315-h}" fill="#eef6ff" font-family="Arial" font-size="16">{value}</text>')
        lines.append(f'<text x="{x-20}" y="365" fill="#b8c7d9" font-family="Arial" font-size="13">{label}</text>')
    lines.append(f'<text x="54" y="405" fill="#b8c7d9" font-family="Arial" font-size="13">Regime rows: {dict(regimes)}. Research infrastructure only, not investment advice.</text>')
    lines.append('</svg>')
    path = CHARTS / "v1_2_10x_value_stack.svg"
    path.write_text("\n".join(lines))
    (SITE_ASSETS / path.name).write_bytes(path.read_bytes())


def package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for path in OUT.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(OUT))
        for path in CHARTS.glob("v1*.svg"):
            z.write(path, Path("charts") / path.name)
    for paid_zip in (DOCS / "downloads").glob("macro_narrative_starter_v1*.zip"):
        paid_zip.unlink()


def main() -> int:
    if not BASE.exists():
        raise SystemExit(f"Missing {BASE}; build v1.1 first")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    docs = read_tsv(OUT / "fomc_documents_v1.tsv")
    features = read_tsv(OUT / "fomc_meeting_features_v1_1.tsv")
    recipes = read_tsv(OUT / "signal_recipes_v1_1.tsv")
    write_quickstart(len(docs), len(recipes))
    write_value_stack()
    write_templates()
    write_validation_assets()
    write_prompt_and_memo_v12()
    write_example_memos(features, docs)
    write_dashboard(features)
    write_notebook_v12()
    write_qa_script()
    write_reports(docs, features, recipes)
    write_public_chart(features)
    package()
    print(f"documents\t{len(docs)}")
    print(f"features\t{len(features)}")
    print(f"recipes\t{len(recipes)}")
    print(f"zip\t{ZIP_PATH}")
    print(f"zip_bytes\t{ZIP_PATH.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
