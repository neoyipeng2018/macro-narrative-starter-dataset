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
OUT = ROOT / "samples" / "fomc_sample_rows.tsv"
CHARTS = ROOT / "charts"

URLS = [
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240320a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240501a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240612a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240731a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20241107a.htm",
    "https://www.federalreserve.gov/newsevents/pressreleases/monetary20241218a.htm",
]

TERM_FAMILIES = {
    "inflation_persistent": ["inflation", "prices", "price stability"],
    "labor_strength": ["job gains", "unemployment", "labor market", "employment"],
    "growth": ["economic activity", "gdp", "growth", "spending"],
    "policy_tight": ["federal funds rate", "restrictive", "tightening"],
    "uncertainty": ["uncertain", "uncertainty", "risks", "risk"],
}


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"For media inquiries.*$", "", text, flags=re.I)
    return text


def extract_date(url: str) -> str:
    m = re.search(r"monetary(\d{8})a", url)
    if not m:
        return ""
    raw = m.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def narrative_terms(text: str) -> str:
    low = text.lower()
    found = []
    for family, terms in TERM_FAMILIES.items():
        if any(t in low for t in terms):
            found.append(family)
    return ";".join(found)


def topic_tags(text: str) -> str:
    low = text.lower()
    tags = []
    for tag, terms in {
        "inflation": ["inflation", "prices"],
        "labor": ["labor", "employment", "unemployment", "job gains"],
        "growth": ["economic activity", "growth", "spending"],
        "policy": ["federal funds rate", "monetary policy", "committee"],
    }.items():
        if any(t in low for t in terms):
            tags.append(tag)
    return ";".join(tags)


def fetch(url: str) -> dict[str, str]:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "macro-narrative-starter/0.1"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    title_node = soup.find("h3") or soup.find("h1") or soup.find("title")
    title = clean_text(title_node.get_text(" ")) if title_node else "FOMC statement"
    article = soup.find("div", class_="col-xs-12 col-sm-8 col-md-8") or soup.find("article") or soup
    paragraphs = [clean_text(p.get_text(" ")) for p in article.find_all("p")]
    text = clean_text(" ".join(p for p in paragraphs if p))
    if len(text) < 400:
        text = clean_text(article.get_text(" "))
    dt = extract_date(url)
    rid = "fomc_" + dt.replace("-", "_") + "_" + hashlib.sha1(url.encode()).hexdigest()[:8]
    return {
        "record_id": rid,
        "source_id": "fomc_statements",
        "date": dt,
        "jurisdiction": "US",
        "title": title,
        "url": url,
        "text": text,
        "text_excerpt": text[:500],
        "token_count_est": str(max(1, len(text.split()) * 4 // 3)),
        "topic_tags": topic_tags(text),
        "narrative_terms": narrative_terms(text),
        "license_note": "Federal Reserve public web page; US federal government source posture, verify page-specific notes for your use case.",
    }


def write_svg(rows: list[dict[str, str]]) -> None:
    CHARTS.mkdir(exist_ok=True)
    counts = []
    for row in rows:
        text = row["text"].lower()
        counts.append((row["date"], text.count("inflation"), text.count("labor") + text.count("employment")))
    max_v = max([1] + [max(a, b) for _, a, b in counts])
    width, height = 860, 360
    left, top, bar_w = 80, 40, 34
    gap = 48
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    lines.append('<rect width="100%" height="100%" fill="#08111f"/>')
    lines.append('<text x="80" y="28" fill="#eef6ff" font-family="Arial" font-size="18">FOMC sample: narrative term counts</text>')
    for i, (dt, inflation, labor) in enumerate(counts):
        x = left + i * gap
        ih = int((inflation / max_v) * 210)
        lh = int((labor / max_v) * 210)
        lines.append(f'<rect x="{x}" y="{300-ih}" width="16" height="{ih}" fill="#7cf2b4"/>')
        lines.append(f'<rect x="{x+18}" y="{300-lh}" width="16" height="{lh}" fill="#87c7ff"/>')
        lines.append(f'<text transform="translate({x+4},330) rotate(45)" fill="#b8c7d9" font-family="Arial" font-size="10">{dt}</text>')
    lines.append('<text x="650" y="42" fill="#7cf2b4" font-family="Arial" font-size="12">inflation</text>')
    lines.append('<text x="650" y="62" fill="#87c7ff" font-family="Arial" font-size="12">labor/employment</text>')
    lines.append('</svg>')
    (CHARTS / "fomc_term_counts.svg").write_text("\n".join(lines))


def main() -> int:
    rows = []
    for url in URLS:
        try:
            rows.append(fetch(url))
        except Exception as exc:
            print(f"WARN failed {url}: {exc}")
    OUT.parent.mkdir(exist_ok=True)
    fields = ["record_id", "source_id", "date", "jurisdiction", "title", "url", "text_excerpt", "token_count_est", "topic_tags", "narrative_terms", "license_note"]
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows([{k: r[k] for k in fields} for r in rows])
    write_svg(rows)
    print(f"rows\t{len(rows)}")
    print(f"sample\t{OUT}")
    print(f"chart\t{CHARTS / 'fomc_term_counts.svg'}")
    return 0 if rows else 1

if __name__ == "__main__":
    raise SystemExit(main())
