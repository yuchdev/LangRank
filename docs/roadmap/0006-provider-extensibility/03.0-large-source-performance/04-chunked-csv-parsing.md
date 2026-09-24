# Subtask 03.0/04 - Chunked CSV Parsing Helpers

**Task:** [03.0 - Large-Source Performance Hardening](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 03 · **Status:** ⬜ Not started

## Goal

Providers parse CSV by iterating rows from a file handle (or a bytes stream) instead of
`raw.content.decode("utf-8").splitlines()`, removing the two full in-memory text copies,
while `parse()` keeps its `list[SourceRecord]` return type (API v1, per the
[stability ADR](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/01-provider-api-stability-adr.md)).

## Baseline

- `tiobe.py`, `pypl.py`, `redmonk.py`, `stackoverflow_survey.py` `parse()` all start with
  `csv.DictReader(raw.content.decode("utf-8").splitlines())`.
- `open_payload_text` from [subtask 03](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/03-streaming-download.md).
- The survey provider's multi-select column fans one CSV row out into many `SourceRecord`s -
  the aggregation (counting respondents per language) is where memory can be bounded.

## Files

| Action | Path                                              | Purpose |
|--------|---------------------------------------------------|---------|
| Modify | `src/langrank/providers/common.py`                | `iter_csv_rows()` helper |
| Modify | `src/langrank/providers/tiobe.py`                 | Use helper |
| Modify | `src/langrank/providers/pypl.py`                  | Use helper |
| Modify | `src/langrank/providers/redmonk.py`               | Use helper |
| Modify | `src/langrank/providers/stackoverflow_survey.py`  | Use helper; aggregate while streaming |
| Create | `tests/unit/test_csv_iteration.py`                | Helper tests |

## Symbols / fields

| Symbol             | Kind      | Type / signature                                                                  | Default | Notes |
|--------------------|-----------|-----------------------------------------------------------------------------------|---------|-------|
| `iter_csv_rows`    | function  | `(payload: FetchPayload, *, delimiter: str = ",", encoding: str = "utf-8-sig") -> Iterator[dict[str, str]]` | - | Generator; closes the handle when exhausted or closed |

## Behaviour & validators

1. `iter_csv_rows` uses `open_payload_text` and `csv.DictReader` over the handle (`newline=""`).
2. Handles BOM (`utf-8-sig`), CRLF, and quoted fields containing newlines identically for path-
   and bytes-backed payloads (today's `splitlines()` breaks quoted newlines - fixed here; pinned by a test).
3. Survey aggregation keeps only per-(year, language) counters in memory, not per-respondent rows.
4. Provider outputs are **byte-for-byte identical** to before on every existing fixture:
   same records, same order, same `raw_record_hash` values (so re-fetch reports 0 updates).
5. `parse()` still returns `list[SourceRecord]`; no Protocol change.

## Tests

| Test function                                         | File                               | Type     | Asserts |
|-------------------------------------------------------|------------------------------------|----------|---------|
| `test_iter_csv_rows_bytes_and_path_identical`         | `tests/unit/test_csv_iteration.py` | Unit     | Same dicts both ways |
| `test_iter_csv_rows_handles_bom_and_crlf`             | `tests/unit/test_csv_iteration.py` | Unit     | BOM stripped from first header |
| `test_iter_csv_rows_quoted_newline`                   | `tests/unit/test_csv_iteration.py` | Unit     | One row, embedded `\n` preserved |
| `test_provider_hashes_unchanged_after_refactor`       | `tests/contract/test_production_providers.py` | Contract | Golden `raw_record_hash` set per fixture (captured before the refactor, committed as `tests/fixtures/<id>/golden_hashes.json`) |
| `test_survey_parse_peak_memory_bounded`               | `tests/benchmarks/test_pipeline_benchmark.py` | Integration (`benchmark`) | 90k-row survey parse peak well below input size × 2 |

## Success criteria

- [ ] `grep -rn "splitlines()" src/langrank/providers` returns nothing.
- [ ] Golden-hash contract test passes for all four production providers.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Providers remain pure over their payload (no DB, no network).
- No pandas or other new dependency.

## Out of scope

- Iterator-returning `parse()`/`normalize()` - deferred by ADR decision 3; reopened only if subtask 05's budget fails.
