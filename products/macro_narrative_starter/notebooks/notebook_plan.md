# Notebook Plan

1. Load source_manifest.tsv and sample_rows.tsv.
2. Validate schema and URLs.
3. Compute simple narrative term families:
   - inflation_up / inflation_down
   - labor_strength / labor_weakness
   - growth_acceleration / growth_slowdown
   - policy_tightening / policy_easing
   - uncertainty_high / uncertainty_low
4. Plot document counts over time by source.
5. Plot narrative term frequency over time.
6. Join to market/economic series only as an example, with explicit leakage-safe lagging.
7. Show train/test split by date; never random-shuffle time series.
8. Export chart PNGs for launch page.
