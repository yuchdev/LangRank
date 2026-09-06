# RedMonk

- What it measures: snapshot rank across RedMonk language reports.
- Official source: https://redmonk.com/sogrady/
- Historical availability: sparse snapshot publications (import targets 2016+).
- Acquisition mechanism: CSV-backed snapshot ingestion with publication-date metadata.
- Imported metrics: `redmonk-rank`.
- Granularity: snapshot (stored as sparse monthly timestamps).
- Language normalization rules: preserve names and alias-map to canonical IDs.
- Known limitations: sparse points are not interpolated.
- Fallbacks: none by default.
- Terms/automation considerations: no aggressive scraping; publication metadata retained.
- Parser/version notes: `redmonk-v1`.
- Last verified date: 2026-09-06.
