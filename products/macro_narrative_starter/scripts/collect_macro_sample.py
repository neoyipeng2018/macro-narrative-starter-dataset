#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples" / "macro_sample_rows.tsv"
CHARTS = ROOT / "charts"

SOURCES = [
    ("fomc_statements", "2024-01-31", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm"),
    ("fomc_statements", "2024-03-20", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240320a.htm"),
    ("fomc_statements", "2024-05-01", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240501a.htm"),
    ("fomc_statements", "2024-06-12", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240612a.htm"),
    ("fomc_statements", "2024-07-31", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240731a.htm"),
    ("fomc_statements", "2024-09-18", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm"),
    ("fomc_statements", "2024-11-07", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20241107a.htm"),
    ("fomc_statements", "2024-12-18", "US", "Federal Reserve FOMC statement", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20241218a.htm"),
    ("bls_releases", "current", "US", "BLS Employment Situation", "https://www.bls.gov/news.release/empsit.nr0.htm"),
    ("bls_releases", "current", "US", "BLS Consumer Price Index", "https://www.bls.gov/news.release/cpi.nr0.htm"),
    ("bls_releases", "current", "US", "BLS Producer Price Index", "https://www.bls.gov/news.release/ppi.nr0.htm"),
    ("bea_releases", "current", "US", "BEA Gross Domestic Product", "https://www.bea.gov/news/current-releases/gross-domestic-product"),
    ("bea_releases", "current", "US", "BEA Personal Income and Outlays", "https://www.bea.gov/news/current-releases/personal-income-and-outlays"),
    ("treasury_speeches", "current", "US", "US Treasury Press Releases", "https://home.treasury.gov/news/press-releases"),
]

TERM_FAMILIES = {
    "inflation": ["inflation", "consumer price", "prices", "price index", "price stability"],
    "labor": ["job", "employment", "unemployment", "labor market", "payroll"],
    "growth": ["gross domestic product", "gdp", "economic activity", "growth", "spending"],
    "policy": ["federal funds rate", "monetary policy", "fiscal", "treasury", "committee"],
    "uncertainty": ["uncertain", "uncertainty", "risks", "risk"],
}

LICENSE_NOTES = {
    "fomc_statements": "Federal Reserve public web page; US federal government source posture, verify page-specific notes for your use case.",
    "bls_releases": "BLS public web page; US federal government source posture, verify page-specific notes for your use case.",
    "bea_releases": "BEA public web page; US federal government source posture, verify page-specific notes for your use case.",
    "treasury_speeches": "US Treasury public web page; US federal government source posture, verify page-specific notes for your use case.",
}


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"Subscribe to receive.*$", "", text, flags=re.I)
    return text


def extract_page_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script", "style", "nav", "footer", "header"]):
        bad.decompose()
    title_node = soup.find("h1") or soup.find("h2") or soup.find("title")
    title = clean_text(title_node.get_text(" ")) if title_node else "Macro public text"
    main = soup.find("main") or soup.find("article") or soup.find("div", id="bodytext") or soup.find("div", class_="field--name-body") or soup
    paragraphs = [clean_text(p.get_text(" ")) for p in main.find_all(["p", "li"])]
    text = clean_text(" ".join(p for p in paragraphs if len(p) > 20))
    if len(text) < 300:
        text = clean_text(main.get_text(" "))
    return title, text


def terms(text: str) -> tuple[str, str]:
    low = text.lower()
    found = []
    tags = []
    for family, needles in TERM_FAMILIES.items():
        count = sum(low.count(n) for n in needles)
        if count:
            found.append(f"{family}:{count}")
            tags.append(family)
    return ";".join(tags), ";".join(found)


def fetch(source_id: str, dt: str, jurisdiction: str, fallback_title: str, url: str) -> dict[str, str]:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "macro-narrative-starter/0.1"})
    resp.raise_for_status()
    title, text = extract_page_text(resp.text)
    if len(text) < 200:
        raise ValueError(f"extracted text too short: {len(text)} chars")
    topic_tags, narrative_terms = terms(text)
    record_date = dt if dt != "current" else date.today().isoformat()
    rid = source_id + "_" + record_date.replace("-", "_") + "_" + hashlib.sha1(url.encode()).hexdigest()[:8]
    return {
        "record_id": rid,
        "source_id": source_id,
        "date": record_date,
        "jurisdiction": jurisdiction,
        "title": title if len(title) > 5 else fallback_title,
        "url": url,
        "text_excerpt": text[:900],
        "token_count_est": str(max(1, len(text.split()) * 4 // 3)),
        "topic_tags": topic_tags,
        "narrative_terms": narrative_terms,
        "license_note": LICENSE_NOTES[source_id],
    }


def write_svg(rows: list[dict[str, str]]) -> None:
    CHARTS.mkdir(exist_ok=True)
    width, height = 940, 420
    source_counts: dict[str, int] = {}
    term_counts: dict[str, int] = {"inflation": 0, "labor": 0, "growth": 0, "policy": 0, "uncertainty": 0}
    for row in rows:
        source_counts[row["source_id"]] = source_counts.get(row["source_id"], 0) + 1
        for part in row["narrative_terms"].split(";"):
            if ":" in part:
                key, value = part.split(":", 1)
                term_counts[key] = term_counts.get(key, 0) + int(value)

    def bar_chart(items: list[tuple[str, int]], title: str, path: Path, color: str) -> None:
        max_v = max([1] + [v for _, v in items])
        lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        lines.append('<rect width="100%" height="100%" fill="#08111f"/>')
        lines.append(f'<text x="64" y="36" fill="#eef6ff" font-family="Arial" font-size="20">{title}</text>')
        for i, (label, value) in enumerate(items):
            x = 72 + i * 150
            h = int((value / max_v) * 260)
            lines.append(f'<rect x="{x}" y="{330-h}" width="70" height="{h}" rx="6" fill="{color}"/>')
            lines.append(f'<text x="{x}" y="{350}" fill="#b8c7d9" font-family="Arial" font-size="12">{label}</text>')
            lines.append(f'<text x="{x+22}" y="{320-h}" fill="#eef6ff" font-family="Arial" font-size="14">{value}</text>')
        lines.append('</svg>')
        path.write_text("\n".join(lines))

    bar_chart(sorted(source_counts.items()), "Sample rows by source", CHARTS / "source_coverage.svg", "#7cf2b4")
    bar_chart(sorted(term_counts.items()), "Narrative term family counts", CHARTS / "narrative_family_counts.svg", "#87c7ff")


def main() -> int:
    rows = []
    for args in SOURCES:
        try:
            rows.append(fetch(*args))
            print(f"OK {args[0]} {args[4]}")
        except Exception as exc:
            print(f"WARN failed {args[0]} {args[4]}: {exc}")
    OUT.parent.mkdir(exist_ok=True)
    fields = ["record_id", "source_id", "date", "jurisdiction", "title", "url", "text_excerpt", "token_count_est", "topic_tags", "narrative_terms", "license_note"]
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    write_svg(rows)
    print(f"rows\t{len(rows)}")
    print(f"sample\t{OUT}")
    print(f"charts\t{CHARTS}")
    return 0 if len(rows) >= 10 else 1

if __name__ == "__main__":
    raise SystemExit(main())
