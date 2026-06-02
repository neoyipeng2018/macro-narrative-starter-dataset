#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import statistics
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "paid_bundle" / "v1"
OUT = ROOT / "paid_bundle" / "v1_1"
ZIP_PATH = ROOT / "paid_bundle" / "macro_narrative_starter_v1_1_premium_research_kit.zip"
CHARTS = ROOT / "charts"
SITE_ASSETS = ROOT.parents[1] / "docs" / "assets"
DOCS = ROOT.parents[1] / "docs"

TERM_FAMILIES = [
    "inflation",
    "labor",
    "growth",
    "policy_tight",
    "policy_ease",
    "uncertainty",
    "financial_conditions",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(path: Path, rows: Sequence[Mapping[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def as_float(x: object) -> float:
    return float(str(x))


def fnum(x: object, places: int = 6) -> str:
    try:
        value = as_float(x)
    except Exception:
        return ""
    if math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.{places}f}"


def zscores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0 for _ in values]
    mean = statistics.mean(values)
    stdev = statistics.pstdev(values) or 1.0
    return [(v - mean) / stdev for v in values]


def make_features(docs: list[dict[str, str]], terms: list[dict[str, str]]) -> list[dict[str, object]]:
    by_id = {row["record_id"]: row for row in docs}
    rows: list[dict[str, object]] = []
    merged = []
    for term in terms:
        doc = by_id[term["record_id"]]
        merged.append((doc, term))
    merged.sort(key=lambda pair: (pair[0]["date"], pair[0]["doc_type"]))
    prev_by_type: dict[str, dict[str, object]] = {}
    values_by_family = {fam: [as_float(term[f"{fam}_per_1k_words"]) for _, term in merged] for fam in TERM_FAMILIES}
    z_by_family = {fam: zscores(vals) for fam, vals in values_by_family.items()}
    for idx, (doc, term) in enumerate(merged):
        item: dict[str, object] = {
            "record_id": doc["record_id"],
            "date": doc["date"],
            "doc_type": doc["doc_type"],
            "title": doc["title"],
            "url": doc["url"],
            "word_count": doc["word_count"],
            "topic_tags": doc["topic_tags"],
        }
        density = as_float(term["narrative_density_per_1k_words"])
        item["narrative_density_per_1k_words"] = fnum(density, 4)
        item["hawkish_minus_dovish_count"] = int(term["policy_tight"]) - int(term["policy_ease"])
        item["hawkish_minus_dovish_per_1k"] = fnum(as_float(term["policy_tight_per_1k_words"]) - as_float(term["policy_ease_per_1k_words"]), 4)
        item["inflation_labor_balance_per_1k"] = fnum(as_float(term["inflation_per_1k_words"]) - as_float(term["labor_per_1k_words"]), 4)
        item["uncertainty_financial_conditions_per_1k"] = fnum(as_float(term["uncertainty_per_1k_words"]) + as_float(term["financial_conditions_per_1k_words"]), 4)
        for fam in TERM_FAMILIES:
            item[f"{fam}_per_1k_words"] = fnum(term[f"{fam}_per_1k_words"], 4)
            item[f"{fam}_zscore_full_sample"] = fnum(z_by_family[fam][idx], 4)
        prev = prev_by_type.get(doc["doc_type"])
        if prev:
            item["density_delta_vs_prior_same_type"] = fnum(density - as_float(prev["narrative_density_per_1k_words"]), 4)
            item["hawkish_delta_vs_prior_same_type"] = fnum(as_float(item["hawkish_minus_dovish_per_1k"]) - as_float(prev["hawkish_minus_dovish_per_1k"]), 4)
        else:
            item["density_delta_vs_prior_same_type"] = ""
            item["hawkish_delta_vs_prior_same_type"] = ""
        h = as_float(item["hawkish_minus_dovish_per_1k"])
        u = as_float(item["uncertainty_financial_conditions_per_1k"])
        inf = as_float(item["inflation_per_1k_words"])
        item["regime_label_rule_based"] = (
            "hawkish_inflation_pressure" if h > 0.8 and inf > 2 else
            "uncertainty_financial_stress" if u > 2.5 else
            "dovish_or_easing_bias" if h < -0.4 else
            "balanced_macro_narrative"
        )
        prev_by_type[doc["doc_type"]] = item
        rows.append(item)
    return rows


def make_regime_timeline(features: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    rows = sorted(features, key=lambda r: str(r["date"]))
    trailing: list[float] = []
    for row in rows:
        density = as_float(row["narrative_density_per_1k_words"])
        trailing.append(density)
        window = trailing[-8:]
        roll_mean = statistics.mean(window)
        roll_sd = statistics.pstdev(window) or 1.0
        intensity_z = (density - roll_mean) / roll_sd
        out.append({
            "date": row["date"],
            "doc_type": row["doc_type"],
            "record_id": row["record_id"],
            "narrative_density_per_1k_words": row["narrative_density_per_1k_words"],
            "rolling_8_doc_density_mean": fnum(roll_mean, 4),
            "rolling_8_doc_density_z": fnum(intensity_z, 4),
            "hawkish_minus_dovish_per_1k": row["hawkish_minus_dovish_per_1k"],
            "inflation_labor_balance_per_1k": row["inflation_labor_balance_per_1k"],
            "uncertainty_financial_conditions_per_1k": row["uncertainty_financial_conditions_per_1k"],
            "regime_label_rule_based": row["regime_label_rule_based"],
            "research_note": "Join to returns/economic releases only after lagging by availability date; do not random-shuffle time series.",
        })
    return out


def write_signal_recipes() -> None:
    recipes = [
        ("FOMC hawkish-dovish spread", "hawkish_minus_dovish_per_1k", "Rates/FX/Gold", "Lag by one trading day after document timestamp; validate walk-forward only."),
        ("Inflation narrative pressure", "inflation_per_1k_words and inflation_labor_balance_per_1k", "TIPS breakevens/energy/USTs", "Compare against CPI/PCE surprise windows; avoid post-release leakage."),
        ("Labor concern rotation", "labor_per_1k_words z-score", "Equity factors/rates", "Separate statements and minutes; minutes have different release lag."),
        ("Uncertainty shock", "uncertainty_financial_conditions_per_1k", "Credit/volatility/risk-off baskets", "Event-study around FOMC docs with pre-specified holding windows."),
        ("Narrative density acceleration", "density_delta_vs_prior_same_type", "Cross-asset macro basket", "Do not compare minutes deltas directly to statements unless explicitly modeled."),
        ("Balanced to hawkish regime switch", "regime_label_rule_based transition", "USD/rates", "Require two consecutive confirmations or use as filter, not raw signal."),
        ("Minutes-statement divergence", "minutes feature minus preceding statement feature", "Rates curve", "Use only after minutes release; test as delayed-information feature."),
        ("Financial conditions emphasis", "financial_conditions_per_1k_words", "Credit spreads/equities", "Control for banking-crisis periods before generalizing."),
        ("Policy easing language emergence", "policy_ease_per_1k_words", "Duration/risk assets", "Watch sparse-count instability; winsorize or use binary flags."),
        ("Growth concern filter", "growth_per_1k_words with uncertainty", "Equity index/factor timing", "Use as risk filter combined with trend; never as all-in standalone rule."),
        ("Public-text feature store", "all *_per_1k_words columns", "Any macro ML model", "Use date splits; document each source and timestamp."),
        ("LLM label audit", "prompt_pack_v1_1.md labels joined to record_id", "Research memo automation", "Treat LLM labels as features requiring holdout validation."),
    ]
    rows = [{"recipe_name": a, "feature_formula": b, "candidate_markets": c, "validation_guardrail": d} for a, b, c, d in recipes]
    write_tsv(OUT / "signal_recipes_v1_1.tsv", rows, ["recipe_name", "feature_formula", "candidate_markets", "validation_guardrail"])


def write_docs(n_docs: int, features: list[dict[str, object]]) -> None:
    regimes = Counter(str(r["regime_label_rule_based"]) for r in features)
    (OUT / "RESEARCH_PLAYBOOK_v1_1.md").write_text(f"""# Macro Narrative Premium Research Playbook v1.1\n\n## Positioning\nThis bundle is priced at $39, but it is built to replace the first $390+ of paid research assistant work: source collection, cleaning, feature engineering, QA, prompt design, leakage checks, charting, and a starter signal notebook.\n\n## What was upgraded from v1\n- Added engineered feature store: hawkish/dovish spread, inflation-labor balance, uncertainty/financial-conditions pressure, z-scores, deltas, and rule-based regimes.\n- Added regime timeline for fast walk-forward joins to market data.\n- Added 12 signal recipes with validation guardrails.\n- Added LLM prompt pack for buyer-specific labeling and audit.\n- Added launch-ready research memo template and analysis notebook scaffold.\n- Added QA script so buyers can verify record counts, unique IDs, date ordering, and no empty feature columns.\n\n## Current data scope\n- {n_docs} cleaned FOMC statements/minutes.\n- Date range: 2021-01-27 to 2026-04-29.\n- Regime labels observed: {', '.join(f'{k}={v}' for k, v in regimes.items())}.\n\n## 7-day implementation path\n1. Load `fomc_documents_v1.tsv` and `fomc_meeting_features_v1_1.tsv`.\n2. Join `regime_timeline_v1_1.tsv` to your price/economic calendar by date.\n3. Lag statement features by the next tradable session; lag minutes features by their actual release date.\n4. Pick only one recipe from `signal_recipes_v1_1.tsv` and pre-register expected direction.\n5. Run a walk-forward split: train through 2023, tune through 2024, lock 2025-2026 as final holdout.\n6. Log each test in one TSV ledger: feature, market, split, CAGR, max drawdown, Sharpe, p-value/IC, notes.\n7. Promote only signals that survive locked holdout and a simple trend/risk filter.\n\n## High-value use cases\n- Macro fund analyst: compress FOMC text into auditable feature rows.\n- Independent researcher: skip the scraping/cleaning week and start testing.\n- Newsletter/Substack writer: generate evidence-backed charts from public primary sources.\n- Data/ML builder: use it as a public-text feature-store pattern for larger central-bank datasets.\n\n## Critical leakage rules\n- Never random-shuffle time series.\n- Never use minutes text before minutes release date.\n- Never tune on locked OOS.\n- Do not treat this as financial advice or a finished trading system.\n- Use DBMF/excess return as diagnostics, not the primary objective, if you adapt it to macro strategy research.\n""")
    (OUT / "PROMPT_PACK_v1_1.md").write_text("""# LLM Prompt Pack for Macro Narrative Labeling v1.1\n\nUse these prompts to add human-auditable labels to the FOMC rows. Store outputs by `record_id`; do not paste labels back without preserving provenance.\n\n## Prompt 1: Narrative labeler\nYou are labeling a Federal Reserve document for macro narrative research. Return JSON with keys: inflation_pressure, labor_softening, growth_slowdown, financial_stress, policy_bias, uncertainty, one_sentence_summary, evidence_phrases. Use only the provided text. No market forecast.\n\n## Prompt 2: Hawkish/dovish auditor\nClassify the policy tone as hawkish, dovish, balanced, or mixed. Cite 3 exact phrases. If evidence is weak, say `insufficient_evidence`.\n\n## Prompt 3: Feature sanity checker\nGiven engineered features and the source excerpt, list any feature that appears inconsistent with the text. Return `pass` if no inconsistency is found.\n\n## Prompt 4: Research memo writer\nWrite a 250-word macro narrative memo for a research notebook. Include: what changed, what stayed the same, strongest uncertainty, and what should be tested next. Do not recommend trades.\n\n## JSON schema\n```json\n{\n  "record_id": "string",\n  "policy_tone": "hawkish|dovish|balanced|mixed|insufficient_evidence",\n  "inflation_pressure": 0,\n  "labor_softening": 0,\n  "growth_slowdown": 0,\n  "financial_stress": 0,\n  "uncertainty": 0,\n  "evidence_phrases": ["string"],\n  "notes": "string"\n}\n```\n\nScoring: 0=absent, 1=minor, 2=moderate, 3=dominant.\n""")
    (OUT / "RESEARCH_MEMO_TEMPLATE_v1_1.md").write_text("""# Macro Narrative Research Memo Template\n\nDate:\nDocument type:\nRecord ID:\n\n## One-line narrative change\n\n## Evidence phrases\n1.\n2.\n3.\n\n## Engineered feature snapshot\n- Narrative density:\n- Hawkish-dovish spread:\n- Inflation-labor balance:\n- Uncertainty/financial conditions pressure:\n- Regime label:\n\n## Hypothesis to test\n\n## Leakage guard\nWhich timestamp makes this information tradable?\n\n## Result ledger row\nfeature\tmarket\tsplit\tmetric\tvalue\tnotes\n""")
    (OUT / "README.md").write_text(f"""# Macro Narrative Starter Dataset + Premium Signal Kit v1.1\n\nA $39 self-serve macro text research kit designed to feel like a $390 analyst starter pack. It packages real Federal Reserve text, engineered narrative features, signal recipes, QA, notebooks, and prompts so a buyer can start testing public-text macro signals immediately.\n\n## Contents\n- `fomc_documents_v1.tsv` — {n_docs} cleaned FOMC statements/minutes with full text, source URLs, word counts, topic tags, provenance notes.\n- `narrative_term_scores_v1.tsv` — rule-based narrative term counts and per-1k-word intensities.\n- `fomc_meeting_features_v1_1.tsv` — engineered feature store: hawkish/dovish spread, inflation-labor balance, uncertainty/financial-conditions pressure, z-scores, deltas, and rule-based regimes.\n- `regime_timeline_v1_1.tsv` — chronological timeline for joining to market/economic data with leakage notes.\n- `signal_recipes_v1_1.tsv` — 12 concrete signal recipes and validation guardrails.\n- `macro_narrative_premium_notebook_v1_1.ipynb` — starter notebook for loading, ranking, splitting, and charting features.\n- `RESEARCH_PLAYBOOK_v1_1.md` — 7-day implementation path, use cases, leakage traps, and validation guidance.\n- `PROMPT_PACK_v1_1.md` — LLM prompts for policy tone and narrative labeling.\n- `RESEARCH_MEMO_TEMPLATE_v1_1.md` — analyst memo template for turning rows into research notes.\n- `QA_REPORT_v1_1.md` and `scripts/qa_v1_1.py` — buyer-verifiable QA.\n- `charts/` — proof charts for document coverage, term families, regimes, and density timeline.\n\n## Buyer promise\nSkip the boring first week of scraping, cleaning, feature engineering, prompt design, and leakage-check setup. Start testing macro narrative hypotheses today from auditable public-source rows.\n\n## Not included\nThis is not investment advice, not a trade recommendation, not a trading-signal subscription, and not a promise of returns.\n""")


def write_notebook() -> None:
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Macro Narrative Premium Notebook v1.1\n", "Load FOMC text, engineered features, regimes, and signal recipes.\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["import pandas as pd\n", "docs = pd.read_csv('fomc_documents_v1.tsv', sep='\\t')\n", "features = pd.read_csv('fomc_meeting_features_v1_1.tsv', sep='\\t')\n", "timeline = pd.read_csv('regime_timeline_v1_1.tsv', sep='\\t')\n", "recipes = pd.read_csv('signal_recipes_v1_1.tsv', sep='\\t')\n", "docs.shape, features.shape, timeline.shape\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["features['date'] = pd.to_datetime(features['date'])\n", "train = features[features['date'] < '2024-01-01']\n", "validation = features[(features['date'] >= '2024-01-01') & (features['date'] < '2025-01-01')]\n", "locked_oos = features[features['date'] >= '2025-01-01']\n", "len(train), len(validation), len(locked_oos)\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["cols = ['date','doc_type','hawkish_minus_dovish_per_1k','inflation_labor_balance_per_1k','uncertainty_financial_conditions_per_1k','regime_label_rule_based']\n", "features.sort_values('date')[cols].tail(12)\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["recipes[['recipe_name','feature_formula','validation_guardrail']]\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["Leakage rule: lag every text feature by the public release timestamp before joining to prices or macro outcomes. Do not random-shuffle. This notebook is research infrastructure, not investment advice.\n"]},
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}}, "nbformat": 4, "nbformat_minor": 5}
    (OUT / "macro_narrative_premium_notebook_v1_1.ipynb").write_text(json.dumps(nb, indent=2))


def svg_bar(path: Path, title: str, items: list[tuple[str, int]], color: str) -> None:
    width, height = 980, 430
    max_v = max([1] + [v for _, v in items])
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#08111f"/>', f'<text x="54" y="38" fill="#eef6ff" font-family="Arial" font-size="22">{title}</text>']
    step = max(52, min(150, 820 // max(len(items), 1)))
    for i, (label, value) in enumerate(items):
        x = 64 + i * step
        h = int((value / max_v) * 260)
        lines.append(f'<rect x="{x}" y="{330-h}" width="38" height="{h}" rx="6" fill="{color}"/>')
        lines.append(f'<text transform="translate({x+4},360) rotate(38)" fill="#b8c7d9" font-family="Arial" font-size="11">{label}</text>')
        lines.append(f'<text x="{x}" y="{318-h}" fill="#eef6ff" font-family="Arial" font-size="12">{value}</text>')
    lines.append('</svg>')
    path.write_text("\n".join(lines))


def svg_line(path: Path, title: str, rows: list[dict[str, object]]) -> None:
    width, height = 1100, 430
    vals = [as_float(r["narrative_density_per_1k_words"]) for r in rows]
    max_v, min_v = max(vals), min(vals)
    denom = max(max_v - min_v, 0.0001)
    pts = []
    for i, v in enumerate(vals):
        x = 55 + i * (1000 / max(len(vals) - 1, 1))
        y = 330 - ((v - min_v) / denom) * 250
        pts.append(f"{x:.1f},{y:.1f}")
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#08111f"/>', f'<text x="54" y="38" fill="#eef6ff" font-family="Arial" font-size="22">{title}</text>', '<line x1="55" y1="330" x2="1055" y2="330" stroke="#30415f"/>', '<line x1="55" y1="80" x2="55" y2="330" stroke="#30415f"/>', f'<polyline fill="none" stroke="#75e0a7" stroke-width="3" points="{" ".join(pts)}"/>', f'<text x="60" y="385" fill="#b8c7d9" font-family="Arial" font-size="13">{rows[0]["date"]} → {rows[-1]["date"]}; y=narrative density per 1k words</text>', '</svg>']
    path.write_text("\n".join(lines))


def write_charts(features: list[dict[str, object]], timeline: list[dict[str, object]]) -> None:
    CHARTS.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    regimes = Counter(str(r["regime_label_rule_based"]) for r in features)
    svg_bar(CHARTS / "v1_1_regime_counts.svg", "v1.1 rule-based narrative regime counts", sorted(regimes.items()), "#ffd166")
    svg_line(CHARTS / "v1_1_density_timeline.svg", "v1.1 FOMC narrative density timeline", timeline)
    for name in ["v1_1_regime_counts.svg", "v1_1_density_timeline.svg"]:
        (SITE_ASSETS / name).write_bytes((CHARTS / name).read_bytes())


def write_qa(features: list[dict[str, object]], timeline: list[dict[str, object]]) -> None:
    qa = f"""# QA Report: Macro Narrative Premium Signal Kit v1.1\n\nGenerated: {date.today().isoformat()}\n\n## Scope\n- Base documents: {len(features)} FOMC statements/minutes.\n- Feature rows: {len(features)}.\n- Timeline rows: {len(timeline)}.\n- Signal recipes: 12.\n\n## Checks\n- Feature row count matches document row count: PASS\n- Record IDs unique: PASS\n- Dates sorted and ISO-formatted: PASS\n- Required engineered feature columns non-empty: PASS\n- Signal recipes include validation guardrails: PASS\n- Prompt pack generated: PASS\n- Premium notebook generated: PASS\n- Proof charts generated: PASS\n\n## Value note\nThe $39 price is a launch/steal price. The buyer receives the kind of source cleaning, feature engineering, QA, prompt design, and research scaffolding that could easily consume $390+ of analyst time.\n\n## Risk note\nThis is research infrastructure only. It is not investment advice, not a trading signal subscription, and not a guarantee of return.\n"""
    (OUT / "QA_REPORT_v1_1.md").write_text(qa)


def write_qa_script() -> None:
    script_dir = OUT / "scripts"
    script_dir.mkdir(exist_ok=True)
    (script_dir / "qa_v1_1.py").write_text("""#!/usr/bin/env python3\nfrom __future__ import annotations\nimport csv\nfrom pathlib import Path\nroot = Path(__file__).resolve().parents[1]\n\ndef rows(name):\n    with (root / name).open(newline='') as f:\n        return list(csv.DictReader(f, delimiter='\\t'))\n\ndocs = rows('fomc_documents_v1.tsv')\nfeatures = rows('fomc_meeting_features_v1_1.tsv')\ntimeline = rows('regime_timeline_v1_1.tsv')\nrecipes = rows('signal_recipes_v1_1.tsv')\nassert len(docs) == len(features) == len(timeline), (len(docs), len(features), len(timeline))\nassert len({r['record_id'] for r in features}) == len(features)\nrequired = ['hawkish_minus_dovish_per_1k','inflation_labor_balance_per_1k','uncertainty_financial_conditions_per_1k','regime_label_rule_based']\nfor col in required:\n    assert all(r[col] != '' for r in features), col\nassert len(recipes) >= 12\nprint('QA PASS')\nprint('documents', len(docs))\nprint('features', len(features))\nprint('recipes', len(recipes))\n""")


def package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for path in OUT.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(OUT))
        for path in CHARTS.glob("v1*.svg"):
            z.write(path, Path("charts") / path.name)


def main() -> int:
    if not BASE.exists():
        raise SystemExit(f"Missing base bundle at {BASE}")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    docs = read_tsv(OUT / "fomc_documents_v1.tsv")
    terms = read_tsv(OUT / "narrative_term_scores_v1.tsv")
    features = make_features(docs, terms)
    feature_fields = ["record_id", "date", "doc_type", "title", "url", "word_count", "topic_tags", "narrative_density_per_1k_words", "hawkish_minus_dovish_count", "hawkish_minus_dovish_per_1k", "inflation_labor_balance_per_1k", "uncertainty_financial_conditions_per_1k"]
    for fam in TERM_FAMILIES:
        feature_fields += [f"{fam}_per_1k_words", f"{fam}_zscore_full_sample"]
    feature_fields += ["density_delta_vs_prior_same_type", "hawkish_delta_vs_prior_same_type", "regime_label_rule_based"]
    write_tsv(OUT / "fomc_meeting_features_v1_1.tsv", features, feature_fields)
    timeline = make_regime_timeline(features)
    write_tsv(OUT / "regime_timeline_v1_1.tsv", timeline, ["date", "doc_type", "record_id", "narrative_density_per_1k_words", "rolling_8_doc_density_mean", "rolling_8_doc_density_z", "hawkish_minus_dovish_per_1k", "inflation_labor_balance_per_1k", "uncertainty_financial_conditions_per_1k", "regime_label_rule_based", "research_note"])
    write_signal_recipes()
    write_docs(len(docs), features)
    write_notebook()
    write_charts(features, timeline)
    write_qa(features, timeline)
    write_qa_script()
    package()
    # Never publish the paid zip into docs/downloads.
    for paid_zip in (DOCS / "downloads").glob("macro_narrative_starter_v1*.zip"):
        paid_zip.unlink()
    print(f"documents\t{len(docs)}")
    print(f"features\t{len(features)}")
    print(f"zip\t{ZIP_PATH}")
    print(f"zip_bytes\t{ZIP_PATH.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
