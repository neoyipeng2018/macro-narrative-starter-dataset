# Macro Narrative Starter Dataset + Signal Notebook

## Promise
Test macro narrative signals today without first building a public-text data pipeline.

## What this product contains
- Source manifest for public/open macro text sources.
- Cleaned sample rows with date, source, title, URL, text, topic tags, narrative term families, and license notes.
- Data schema and QA rules.
- Notebook plan for narrative momentum, uncertainty proxies, topic drift, and leakage-safe signal tests.
- Chart/spec examples for launch posts and checkout screenshots.

## Who this is for
- Systematic macro researchers who want a text-data starter kit.
- Analysts and writers who want auditable source-backed charts.
- AI/data founders building finance research tooling.
- Students or academics prototyping macro NLP work.

## Who this is not for
- Anyone expecting guaranteed trading returns.
- Anyone needing proprietary alternative data.
- Anyone unwilling to verify source terms for their specific use case.

## License / provenance posture
This product prioritizes US government/public-domain style sources and open metadata. Every source gets a manifest row with URL and license/terms notes. Before paid release, each bundled source must pass the source QA checklist. Where redistribution is uncertain, the paid product should include reproducible scripts and metadata rather than repackaged full text.

## Initial SKUs
- Free sample: selected rows, manifest, README, 2 charts.
- Starter: one source family, simple notebook, prompt recipes.
- Flagship: multi-source bundle, full notebook, charts, QA report.
- Team license: flagship plus internal sharing rights and update access.

## Build status
v0.1 serious scaffold with real sample artifacts:
- `samples/fomc_sample_rows.tsv`: 8 fetched FOMC statement rows from 2024.
- `charts/fomc_term_counts.svg`: first launch-page proof chart.
- `scripts/collect_fomc_sample.py`: reproducible collector for current sample.
- `scripts/qa_sample.py`: QA checks for manifest membership, URLs, dates, token count, and license notes.

Next: expand real row collection beyond FOMC, generate 2 more charts, and publish the free sample page/repo.


## v1 real product bundle
The paid v1 bundle is now built at `paid_bundle/macro_narrative_starter_v1.zip`.

Contents:
- 87 cleaned FOMC statement/minutes documents from 2021-01-27 through 2026-04-29.
- 44 statements and 43 minutes.
- Full cleaned text, excerpts, URLs, document dates, word/token counts, topic tags, narrative term counts, and provenance notes.
- `narrative_term_scores_v1.tsv` with per-document term family counts and per-1k-word intensities.
- `source_manifest_v1.tsv`.
- `macro_narrative_v1_notebook.ipynb`.
- `QA_REPORT_v1.md`.
- SVG proof charts.

Gumroad upload file:
`/Users/nyp/Documents/my_life/1000_to_10000_nopermission/products/macro_narrative_starter/paid_bundle/macro_narrative_starter_v1.zip`
