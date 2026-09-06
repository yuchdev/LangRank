# TIOBE

- What it measures: search/visibility-based language ranking.
- Official source: https://www.tiobe.com/tiobe-index/
- Historical availability: monthly historical snapshots (import targets 2016+).
- Acquisition mechanism: CSV-backed ingestion with mode metadata (`auto`/`official`/`fallback`).
- Imported metrics: `tiobe-rank`, `tiobe-rating`.
- Granularity: monthly.
- Language normalization rules: preserve source names; map aliases via canonical map; no synthetic splits.
- Known limitations: fallback reconstructions are marked as `third_party_reconstruction` provenance.
- Fallbacks: documented provenance flag in metadata.
- Terms/automation considerations: no CAPTCHA bypass or restricted-access circumvention.
- Parser/version notes: `tiobe-v1`.
- Last verified date: 2026-09-06.
