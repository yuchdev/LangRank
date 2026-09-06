# PYPL

- What it measures: tutorial-search share by language.
- Official source: https://pypl.github.io/PYPL.html
- Historical availability: monthly published history (import targets 2016+).
- Acquisition mechanism: CSV-backed ingestion of published history.
- Imported metrics: `pypl-rank`, `pypl-share`.
- Granularity: monthly.
- Language normalization rules: keep `C/C++` combined as canonical `c-cpp`; do not split.
- Known limitations: source categories may be combined and are preserved.
- Fallbacks: optional reconstructed values can be marked via `is_derived`/`derivation_method`.
- Terms/automation considerations: respect source access constraints.
- Parser/version notes: `pypl-v1`.
- Last verified date: 2026-09-06.
