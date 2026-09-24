# Subtask 04.0/06 - Raw-data import: derived respondent shares

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Support `langrank import --rating jetbrains <raw.csv>` over an anonymized raw-response file,
computing unweighted per-language respondent shares as **derived** `-raw` metrics.

## Baseline

`cli.py:import_data` passes `FetchPayload(content=path.read_bytes())` - the whole file in
memory; raw files are hundreds of MB. Streaming is
[Milestone 0006 Task 03.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-030---large-source-performance-hardening);
here, parse with `csv.reader` over `io.TextIOWrapper(io.BytesIO(...))` and count in one
pass without building per-row objects.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/jetbrains.py` | `_parse_raw`, raw branch in `parse/normalize` |
| Create | `tests/unit/test_jetbrains_raw.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `_detect_survey_year` | function | `(header: list[str]) -> int` | From registry column prefixes; `ParseError` if ambiguous |
| `_parse_raw` | function | `(content: bytes) -> list[SourceRecord]` | One record per (metric, language) |
| `RAW_DERIVATION` | const | `str` | `"unweighted_respondent_share"` |

## Behaviour & validators

1. Denominator = respondents who answered the question (≥1 option selected); stored as
   `sample_size` and in `metadata_json["denominator"]`.
2. `is_derived=True`, `derivation_method=RAW_DERIVATION`, metric ID with `-raw` suffix.
3. No response-level data is stored or cached beyond the user's cache dir (per source note).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_jetbrains_raw_share_math` | `tests/unit/test_jetbrains_raw.py` | Unit | Hand-computed shares |
| `test_jetbrains_raw_is_derived` | `tests/unit/test_jetbrains_raw.py` | Unit | Flag, method, `-raw` IDs |
| `test_jetbrains_raw_year_detection` | `tests/unit/test_jetbrains_raw.py` | Unit | Year from header; ambiguity raises |
| `test_jetbrains_raw_non_respondents_excluded` | `tests/unit/test_jetbrains_raw.py` | Unit | Denominator excludes blanks |

## Success criteria

- [ ] Raw and published values never share a metric ID.

## Constraints

- Pure over the input bytes.

## Out of scope

- Reweighting to match published figures.
