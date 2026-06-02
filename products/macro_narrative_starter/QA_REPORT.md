# QA Report: Macro Narrative Starter v0.1 Free Sample

Generated: 2026-06-02

## Scope
- Free sample rows: 8
- Source ids: fomc_statements
- Files checked: source manifest, macro sample rows, chart artifacts, collection scripts, QA scripts.

## Checks
- Record IDs unique: PASS
- Source IDs present in manifest: PASS
- URLs are HTTP(S): PASS
- Dates are ISO format: PASS
- Token count estimates above minimum: PASS
- License/provenance note present on each row: PASS
- Guard script confirms no reserve/spend breach: PASS

## Known limitations
- v0.1 is intentionally small and currently FOMC-heavy.
- BLS blocked automated collection during first pass; BEA/Treasury require source-specific collectors or manually verified endpoints.
- This is a research workflow/data-pack starter, not investment advice or a promise of trading returns.
- Users must verify source terms for their own commercial/internal use case.

## Next data expansion
- Add BEA/BLS/Treasury rows through verified endpoints or manual source-specific collectors.
- Add source coverage beyond FOMC.
- Add notebook outputs for leakage-safe narrative momentum examples.
