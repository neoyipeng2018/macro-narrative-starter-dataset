#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'daily_reports'

summary = subprocess.check_output(['python3', str(ROOT / 'scripts' / 'summarize.py')], text=True)
guard = subprocess.run(['python3', str(ROOT / 'scripts' / 'guard.py')], text=True, capture_output=True)

today = date.today().isoformat()
report = """# Daily Report: {today}

## Guard
```text
{guard}
```

## Summary
```text
{summary}
```

## Bottleneck
Product is not launched yet. The biggest bottleneck is source verification and producing a credible free sample with real rows, charts, and README proof.

## Action taken
Initialized serious no-permission operating folder, ledgers, product scaffold, source manifest, schema, checkout copy, launch templates, and guard/summarize scripts.

## Next action
Verify source terms and collect real sample rows for the Macro Narrative Starter free sample. Then generate first charts and publish a sample repo/page.

## Safety
No actual spend has been executed. Reserve and ops-card rows are planned/user-to-confirm only. Agent has no money custody.
""".format(today=today, guard=guard.stdout.strip(), summary=summary.strip())
REPORTS.mkdir(exist_ok=True)
path = REPORTS / f'{today}.md'
path.write_text(report)
print(path)
