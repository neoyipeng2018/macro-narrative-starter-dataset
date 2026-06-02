# Macro Narrative Backtesting Research Accelerator

## Promise
Test public-text macro narrative ideas and run leakage-aware event-study backtests without first building a data pipeline, feature store, price importer, validation ledger, QA workflow, prompt pack, and notebook scaffold.

## Positioning
The paid v1.3 bundle is priced at `$49`, but it is intentionally built to deliver at least 10x buyer value. Conservative replacement-value estimate: `$1,090+`. The value comes from compressing source collection, cleaning, schema design, feature engineering, price-data import plumbing, event-window backtesting, leakage guardrails, QA, charts, prompts, notebooks, example memos, and experiment tracking into one auditable bundle.

## Who this is for
- Systematic macro researchers who want a public-text starter feature store plus a backtesting harness.
- Macro narrative researchers testing FOMC language features against rates, USD, gold, equities, or managed-futures diagnostics.
- Analysts and writers who want auditable source-backed FOMC narrative charts and event-study scaffolds.
- AI/data founders building finance research tooling.
- Students or academics prototyping macro NLP workflows.

## Who this is not for
- Anyone expecting guaranteed trading returns.
- Anyone needing proprietary alternative data.
- Anyone unwilling to run their own validation on market data.
- Anyone treating synthetic smoke-test output as market evidence.

## Free sample
The public repo keeps a free sample so buyers can inspect schema, source posture, QA style, and charts before buying.

## Paid v1.3 backtesting bundle
The paid bundle is local-only and excluded from the public repo:

```text
paid_bundle/macro_narrative_starter_v1_3_backtesting_research_accelerator.zip
```

Contents include:
- `BACKTESTING_START_HERE_v1_3.md` — fastest path from download to first backtest.
- `scripts/backtest_macro_narrative.py` — event-study backtester with lag days, holding window, split date, target asset, and results TSV.
- `scripts/fetch_price_data_yahoo.py` — no-key Yahoo adjusted-close fetcher for ETF proxy columns.
- `signal_recipe_backtest_configs_v1_3.tsv` — starter feature/asset/horizon backtest configs.
- `market_proxy_map_v1_3.tsv` — rates, equities, gold, USD, and DBMF proxy map with caveats.
- `templates/backtest_experiment_ledger_v1_3.tsv` — validation/OOS/DBMF-aware experiment ledger.
- `BACKTESTING_VALIDATION_CHECKLIST_v1_3.md` — release timing, OOS leakage, baseline, and DBMF-diagnostic checklist.
- `macro_narrative_backtesting_notebook_v1_3.ipynb` — notebook scaffold for running and summarizing backtests.
- `VALUE_STACK_BACKTESTING_v1_3.md` / `.tsv` — explicit $1,090+ replacement-value stack.
- `fomc_documents_v1.tsv` — 87 cleaned FOMC statement/minutes documents from 2021-01-27 through 2026-04-29.
- `narrative_term_scores_v1.tsv` — narrative term family counts and per-1k-word intensities.
- `fomc_meeting_features_v1_1.tsv` — engineered feature store with hawkish/dovish spread, inflation-labor balance, uncertainty/financial-conditions pressure, z-scores, deltas, and regimes.
- `regime_timeline_v1_1.tsv` — chronological timeline for joining to market/economic data after leakage-safe lagging.
- `signal_recipes_v1_1.tsv` — 12 research recipes with formulas, candidate markets, and validation guardrails.
- `PROMPT_PACK_v1_2.md`, `RESEARCH_MEMO_TEMPLATE_v1_2.md`, examples, dashboard, non-coder guide, ROI calculator, QA scripts, and SVG proof charts.

## Gumroad upload file

```text
/Users/nyp/Documents/my_life/1000_to_10000_nopermission/products/macro_narrative_starter/paid_bundle/macro_narrative_starter_v1_3_backtesting_research_accelerator.zip
```

## License / provenance posture
This product prioritizes US government/public-source materials and records every source with URL and license/terms notes. Buyers should verify source terms for their specific use case. The product is research infrastructure, not investment advice, not a trading signal subscription, and not a guarantee of returns.
