# Subtask 03.0/04 - Curated edition dataset & fetch/import path

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 03 · **Status:** ⬜ Not started

## Goal

Transcribe the published editions into a bundled CSV and implement `fetch()` (bundled data,
`--source bundled`) plus the `langrank import` path for new editions.

## Baseline

`TiobeProvider.fetch` bundled-CSV pattern; `cli.py:import_data`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/data/ieee_spectrum.csv` | Columns `year,profile,rank,language,score,source_url,published_at,methodology_version` |
| Modify | `src/langrank/providers/ieee_spectrum.py` | `fetch()` |
| Create | `tests/unit/test_ieee_spectrum_fetch.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `DATA_PATH` | const | `Path` | `providers/data/ieee_spectrum.csv` |
| `fetch` | method | `(request: FetchRequest) -> FetchPayload` | `source` ∈ `{None,"auto","bundled"}`; else `ProviderError` |

## Behaviour & validators

1. Artifact `url` = the provider homepage; `metadata_json={"mode": "bundled", "provenance": "manual_transcription"}`.
2. `since/until/years` filtering happens after parse (subtask 05).
3. `import` CSVs use the same header; mismatch → `ParseError` in subtask 05.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ieee_fetch_reads_bundled_csv` | `tests/unit/test_ieee_spectrum_fetch.py` | Unit | Payload bytes = file bytes |
| `test_ieee_fetch_unknown_source_raises` | `tests/unit/test_ieee_spectrum_fetch.py` | Unit | `ProviderError` |
| `test_ieee_bundled_csv_header` | `tests/unit/test_ieee_spectrum_fetch.py` | Unit | Exact header |

## Success criteria

- [ ] CSV covers every edition in the source note with a `source_url` per row.

## Constraints

- No network access; no scraping.

## Out of scope

- Automated edition discovery (Milestone 0004).
