#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "fomc_sample_rows.tsv"
MANIFEST = ROOT / "source_manifest.tsv"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main() -> int:
    rows = read_tsv(SAMPLE)
    manifest = {r["source_id"] for r in read_tsv(MANIFEST)}
    problems: list[str] = []
    ids = set()
    for i, row in enumerate(rows, start=1):
        if row["record_id"] in ids:
            problems.append(f"row {i}: duplicate record_id {row['record_id']}")
        ids.add(row["record_id"])
        if row["source_id"] not in manifest:
            problems.append(f"row {i}: source_id not in manifest")
        if not row["date"] or len(row["date"]) != 10:
            problems.append(f"row {i}: invalid date {row['date']}")
        parsed = urlparse(row["url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            problems.append(f"row {i}: invalid url {row['url']}")
        if int(row["token_count_est"] or 0) < 100:
            problems.append(f"row {i}: token_count_est too low")
        if not row["license_note"]:
            problems.append(f"row {i}: missing license_note")
    if problems:
        print("QA FAIL")
        for p in problems:
            print("-", p)
        return 1
    print("QA PASS")
    print(f"rows\t{len(rows)}")
    print(f"sources\t{sorted(manifest)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
