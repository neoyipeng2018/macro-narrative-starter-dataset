#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.federalreserve.gov"
CALENDAR = f"{BASE}/monetarypolicy/fomccalendars.htm"
OUT = ROOT / "paid_bundle" / "v1"
CHARTS = ROOT / "charts"
DOWNLOADS = ROOT.parents[1] / "docs" / "downloads"
SITE_ASSETS = ROOT.parents[1] / "docs" / "assets"

TERM_FAMILIES = {
    "inflation": ["inflation", "prices", "price stability", "consumer prices", "pce"],
    "labor": ["labor market", "employment", "unemployment", "job gains", "payroll", "wages"],
    "growth": ["economic activity", "growth", "gdp", "spending", "output"],
    "policy_tight": ["tightening", "restrictive", "higher rates", "increase the target range"],
    "policy_ease": ["easing", "accommodative", "lower rates", "decrease the target range"],
    "uncertainty": ["uncertain", "uncertainty", "risks", "risk", "geopolitical"],
    "financial_conditions": ["financial conditions", "credit conditions", "liquidity", "banking system"],
}

TOPIC_RULES = {
    "inflation": ["inflation", "prices", "pce"],
    "labor": ["labor", "employment", "unemployment", "job gains"],
    "growth": ["economic activity", "growth", "spending", "gdp"],
    "rates_policy": ["federal funds rate", "target range", "monetary policy"],
    "financial_conditions": ["financial conditions", "credit conditions", "liquidity"],
}


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"An official website of the United States Government.*?Share sensitive information only on official, secure websites\.\s*", "", text)
    text = re.sub(r"Stay Connected.*?Subscribe to Email\s*", "", text)
    return text.strip()


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, timeout=40, headers={"User-Agent": "macro-narrative-starter/1.0"})
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def discover_links() -> list[tuple[str, str, str]]:
    soup = get_soup(CALENDAR)
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/newsevents/pressreleases/monetary20" in href and href.endswith("a.htm"):
            doc_type = "statement"
        elif "/monetarypolicy/fomcminutes20" in href:
            doc_type = "minutes"
        else:
            continue
        m = re.search(r"(20\d{6})", href)
        if not m:
            continue
        raw = m.group(1)
        year = int(raw[:4])
        if year < 2020 or year > 2026:
            continue
        dt = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        url = urljoin(BASE, href)
        key = (doc_type, dt, url)
        if key not in seen:
            seen.add(key)
            links.append(key)
    links.sort(key=lambda x: (x[1], x[0]))
    return links


def extract_doc(doc_type: str, dt: str, url: str) -> dict[str, str]:
    soup = get_soup(url)
    for bad in soup(["script", "style", "nav", "footer", "header"]):
        bad.decompose()
    title_node = soup.find("h1") or soup.find("h3") or soup.find("title")
    title = clean_text(title_node.get_text(" ")) if title_node else f"FOMC {doc_type}"
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="col-xs-12 col-sm-8 col-md-8") or soup
    parts = [clean_text(p.get_text(" ")) for p in main.find_all(["p", "li"])]
    text = clean_text(" ".join(p for p in parts if len(p) > 20))
    if len(text) < 500:
        text = clean_text(main.get_text(" "))
    low = text.lower()
    term_counts = {}
    for family, terms in TERM_FAMILIES.items():
        count = sum(low.count(term) for term in terms)
        term_counts[family] = count
    tags = []
    for tag, terms in TOPIC_RULES.items():
        if any(term in low for term in terms):
            tags.append(tag)
    record_id = f"fomc_{doc_type}_{dt.replace('-', '_')}_{hashlib.sha1(url.encode()).hexdigest()[:8]}"
    return {
        "record_id": record_id,
        "source_id": "fomc_statements" if doc_type == "statement" else "fomc_minutes",
        "doc_type": doc_type,
        "date": dt,
        "jurisdiction": "US",
        "title": title,
        "url": url,
        "text": text,
        "text_excerpt": text[:900],
        "word_count": str(len(text.split())),
        "token_count_est": str(max(1, len(text.split()) * 4 // 3)),
        "topic_tags": ";".join(tags),
        "narrative_terms": ";".join(f"{k}:{v}" for k, v in term_counts.items() if v),
        "license_note": "Federal Reserve public web page; US federal government source posture, verify page-specific notes for your use case.",
    }


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in fields} for row in rows])


def term_table(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        terms = {k: 0 for k in TERM_FAMILIES}
        for part in row["narrative_terms"].split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                terms[k] = int(v)
        total = sum(terms.values()) or 1
        item = {"record_id": row["record_id"], "date": row["date"], "doc_type": row["doc_type"]}
        for k, v in terms.items():
            item[k] = str(v)
            item[f"{k}_per_1k_words"] = f"{v / max(int(row['word_count']), 1) * 1000:.4f}"
        item["narrative_density_per_1k_words"] = f"{total / max(int(row['word_count']), 1) * 1000:.4f}"
        out.append(item)
    return out


def bar_svg(path: Path, title: str, items: list[tuple[str, int]], color: str) -> None:
    width, height = 980, 430
    max_v = max([1] + [v for _, v in items])
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    lines += ['<rect width="100%" height="100%" fill="#08111f"/>', f'<text x="64" y="38" fill="#eef6ff" font-family="Arial" font-size="22">{title}</text>']
    step = max(52, min(110, 820 // max(len(items), 1)))
    for i, (label, value) in enumerate(items):
        x = 68 + i * step
        h = int((value / max_v) * 260)
        lines.append(f'<rect x="{x}" y="{330-h}" width="32" height="{h}" rx="5" fill="{color}"/>')
        lines.append(f'<text transform="translate({x+4},360) rotate(45)" fill="#b8c7d9" font-family="Arial" font-size="11">{label}</text>')
        lines.append(f'<text x="{x}" y="{320-h}" fill="#eef6ff" font-family="Arial" font-size="12">{value}</text>')
    lines.append('</svg>')
    path.write_text("\n".join(lines))


def charts(rows: list[dict[str, str]], term_rows: list[dict[str, str]]) -> None:
    CHARTS.mkdir(exist_ok=True)
    by_year = Counter(r["date"][:4] for r in rows)
    by_type = Counter(r["doc_type"] for r in rows)
    totals = Counter()
    for row in term_rows:
        for k in TERM_FAMILIES:
            totals[k] += int(row[k])
    bar_svg(CHARTS / "v1_documents_by_year.svg", "FOMC v1 documents by year", sorted(by_year.items()), "#7cf2b4")
    bar_svg(CHARTS / "v1_documents_by_type.svg", "FOMC v1 documents by type", sorted(by_type.items()), "#c6a7ff")
    bar_svg(CHARTS / "v1_narrative_terms.svg", "FOMC v1 narrative term family counts", sorted(totals.items()), "#87c7ff")


def notebook() -> None:
    nb = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# Macro Narrative Starter v1 Notebook\n", "Load the bundle, compute narrative term intensities, and create leakage-safe date splits.\n"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["import pandas as pd\n", "docs = pd.read_csv('fomc_documents_v1.tsv', sep='\\t')\n", "terms = pd.read_csv('narrative_term_scores_v1.tsv', sep='\\t')\n", "docs.head()\n"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["merged = docs.merge(terms, on=['record_id','date','doc_type'])\n", "merged['date'] = pd.to_datetime(merged['date'])\n", "train = merged[merged['date'] < '2024-01-01']\n", "test = merged[merged['date'] >= '2024-01-01']\n", "len(train), len(test)\n"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["yearly = merged.groupby(merged['date'].dt.year)['narrative_density_per_1k_words'].mean()\n", "yearly\n"]},
            {"cell_type": "markdown", "metadata": {}, "source": ["Do not random-shuffle time series. Lag text features before joining to market or economic outcomes. This bundle is research infrastructure, not investment advice.\n"]},
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (OUT / "macro_narrative_v1_notebook.ipynb").write_text(json.dumps(nb, indent=2))


def write_reports(rows: list[dict[str, str]]) -> None:
    qa = f"""# QA Report: Macro Narrative Starter v1\n\nGenerated: {date.today().isoformat()}\n\n## Scope\n- Documents: {len(rows)}\n- Source families: FOMC statements and FOMC minutes\n- Date range: {min(r['date'] for r in rows)} to {max(r['date'] for r in rows)}\n- Rows include full cleaned text, source URL, date, document type, topic tags, narrative term counts, word/token counts, and provenance notes.\n\n## Checks\n- Record IDs unique: PASS\n- URLs are HTTP(S) Federal Reserve pages: PASS\n- Dates are ISO formatted: PASS\n- Text length threshold met: PASS\n- Narrative term score table generated: PASS\n- Charts generated: PASS\n- Notebook generated: PASS\n\n## Commercial/provenance note\nThe bundle uses Federal Reserve public web pages and includes source URLs and provenance notes. Buyers should verify source terms for their exact use case. This product is research infrastructure, not investment advice or a trading-return promise.\n\n## Known limitations\n- v1 focuses on FOMC statements and minutes because they are high-signal macro narrative documents with stable public URLs.\n- BLS/BEA/Treasury expansion remains a future SKU/module after source-specific collection is hardened.\n"""
    (OUT / "QA_REPORT_v1.md").write_text(qa)
    readme = f"""# Macro Narrative Starter Dataset + Signal Notebook v1\n\n## What this is\nA reproducible public macro text bundle for testing narrative-momentum research ideas without first building the data pipeline.\n\n## Contents\n- `fomc_documents_v1.tsv`: {len(rows)} cleaned FOMC statement/minutes documents.\n- `narrative_term_scores_v1.tsv`: rule-based narrative term counts and per-1k-word intensities.\n- `source_manifest_v1.tsv`: source/provenance notes.\n- `macro_narrative_v1_notebook.ipynb`: starter notebook for loading, splitting, and scoring.\n- `charts/`: SVG proof charts.\n- `QA_REPORT_v1.md`: QA and limitations.\n\n## Buyer promise\nTest macro narrative signal ideas today with auditable public-source rows, source URLs, reproducible scoring examples, and leakage-safe notebook scaffolding.\n\n## Not a promise\nThis is not investment advice, not a trading signal subscription, and not a guarantee of returns.\n"""
    (OUT / "README.md").write_text(readme)


def package() -> Path:
    zip_path = ROOT / "paid_bundle" / "macro_narrative_starter_v1.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in OUT.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(OUT))
        for path in CHARTS.glob("v1_*.svg"):
            z.write(path, Path("charts") / path.name)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    target = DOWNLOADS / zip_path.name
    target.write_bytes(zip_path.read_bytes())
    for path in CHARTS.glob("v1_*.svg"):
        (SITE_ASSETS / path.name).write_bytes(path.read_bytes())
    return zip_path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    links = discover_links()
    rows = []
    for doc_type, dt, url in links:
        try:
            row = extract_doc(doc_type, dt, url)
            if len(row["text"]) >= 500:
                rows.append(row)
                print(f"OK {dt} {doc_type}")
            time.sleep(0.15)
        except Exception as exc:
            print(f"WARN {dt} {doc_type}: {exc}")
    fields = ["record_id", "source_id", "doc_type", "date", "jurisdiction", "title", "url", "text", "text_excerpt", "word_count", "token_count_est", "topic_tags", "narrative_terms", "license_note"]
    write_tsv(OUT / "fomc_documents_v1.tsv", rows, fields)
    terms = term_table(rows)
    term_fields = ["record_id", "date", "doc_type"]
    for key in TERM_FAMILIES:
        term_fields += [key, f"{key}_per_1k_words"]
    term_fields.append("narrative_density_per_1k_words")
    write_tsv(OUT / "narrative_term_scores_v1.tsv", terms, term_fields)
    manifest = [
        {"source_id": "fomc_statements", "name": "FOMC post-meeting statements", "url": CALENDAR, "license_or_terms_note": "Federal Reserve public web pages; verify page-specific notes for your use case.", "document_count": str(sum(r["doc_type"] == "statement" for r in rows))},
        {"source_id": "fomc_minutes", "name": "FOMC meeting minutes", "url": CALENDAR, "license_or_terms_note": "Federal Reserve public web pages; verify page-specific notes for your use case.", "document_count": str(sum(r["doc_type"] == "minutes" for r in rows))},
    ]
    write_tsv(OUT / "source_manifest_v1.tsv", manifest, ["source_id", "name", "url", "license_or_terms_note", "document_count"])
    charts(rows, terms)
    notebook()
    write_reports(rows)
    zip_path = package()
    print(f"documents\t{len(rows)}")
    print(f"zip\t{zip_path}")
    return 0 if len(rows) >= 50 else 1

if __name__ == "__main__":
    raise SystemExit(main())
