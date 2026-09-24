# Subtask 02.0/03 - Deterministic Bundle Writers & Checksums

**Task:** [02.0 - Dataset Release Workflow](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 02 · **Status:** ⬜ Not started

## Goal

Write each bundle file deterministically from `ReleaseRow`s and the manifest, and produce a
`sha256sum`-compatible `checksums.txt`.

## Baseline

- `exports/csv_export.py` uses `csv.DictWriter` over `QueryRow` fields; no determinism
  guarantees for floats or line endings.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/langrank/release/writers.py` | Writers below |
| Create | `tests/unit/test_release_writers.py` | Writer tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `HISTORY_CSV` / `HISTORY_JSON` / `SNAPSHOT_SQLITE` / `METADATA_JSON` / `CHECKSUMS_TXT` | constants | `str` | `"langrank-history.csv"`, `"langrank-history.json"`, `"langrank.sqlite"`, `"metadata.json"`, `"checksums.txt"` | |
| `write_history_csv` | function | `(rows: Sequence[ReleaseRow], path: Path) -> None` | - | Header = `RELEASE_COLUMNS`; `lineterminator="\n"`; floats via `repr()`; `None` → empty cell; `metadata_json` as compact sorted JSON |
| `write_history_json` | function | `(rows: Sequence[ReleaseRow], path: Path) -> None` | - | JSON array, `sort_keys=True`, `indent=2`, trailing `\n` |
| `describe_file` | function | `(path: Path, *, media_type: str, byte_reproducible: bool) -> ReleaseFile` | - | Streams sha256 in 1 MiB chunks |
| `write_checksums` | function | `(directory: Path, names: Sequence[str]) -> Path` | - | Lines `"{sha256}  {name}\n"` sorted by name |

## Behaviour & validators

1. Same input rows → byte-identical CSV and JSON (no timestamps written by writers).
2. UTF-8 without BOM, `\n` only, on every platform.
3. `write_checksums` includes `metadata.json` and all data files but never itself.
4. Writers do not sort - they trust `release_rows` ordering; a debug `assert` checks
   ordering is non-decreasing on the natural key.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_history_csv_is_byte_identical_across_runs` | `tests/unit/test_release_writers.py` | Unit | two writes → same bytes |
| `test_history_csv_preserves_missing_as_empty` | same | Unit | `rank=None` → empty cell, not `0` |
| `test_history_json_sorted_keys_and_newline` | same | Unit | |
| `test_checksums_match_sha256sum_format` | same | Unit | regex `^[0-9a-f]{64}  \S+$`; recomputed hashes match |
| `test_checksums_excludes_itself` | same | Unit | |

## Success criteria

- [ ] Missing values stay missing in every format ([CLAUDE.md](/CLAUDE.md)).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Standard library only (`csv`, `json`, `hashlib`).

## Out of scope

- Orchestration, temp-dir handling - [04](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/04-release-service.md).
