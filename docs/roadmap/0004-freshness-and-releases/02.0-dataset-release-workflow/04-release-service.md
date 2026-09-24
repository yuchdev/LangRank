# Subtask 02.0/04 - ReleaseService Assembly

**Task:** [02.0 - Dataset Release Workflow](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Assemble a complete bundle: query data, apply redistribution exclusions, gather
provenance/methodology/warnings, write files into a temp dir, compute checksums, build the
manifest, and atomically move the result into place.

## Baseline

- `ValidationService.validate()` returns a `ValidationReport` over the whole DB.
- `ProviderMetadata.caveats`, `.methodology_notes`, and (after 01.0/05) `.source_policy`.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/langrank/services/release.py` | `ReleaseRequest`, `ReleaseResult`, `ReleaseService` |
| Create | `tests/integration/test_release.py` | Fixture-driven end-to-end service tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `ReleaseRequest` | frozen dataclass | `output_dir: Path`, `since: date \| None`, `until: date \| None`, `ratings: list[str]`, `generated_at: datetime \| None`, `force: bool` | `None`, `None`, `[]`, `None`, `False` | |
| `ReleaseResult` | frozen dataclass | `output_dir: Path`, `manifest: ReleaseManifest`, `row_count: int` | - | |
| `ReleaseService.__init__` | method | `(database: Database, registry: ProviderRegistry)` | - | |
| `ReleaseService.build` | method | `(request: ReleaseRequest) -> ReleaseResult` | - | |
| `resolve_generated_at` | function | `(explicit: datetime \| None, env: Mapping[str, str]) -> datetime` | - | explicit > `SOURCE_DATE_EPOCH` > `datetime.now(UTC)` |

## Behaviour & validators

1. Output guard: if `output_dir` exists and is non-empty and not `force` → `StorageError`.
   With `force`, only a directory containing a prior `metadata.json` may be replaced.
2. Build in `output_dir.parent / f".{name}.tmp-<uuid>"`; on success `os.replace` to
   `output_dir`; on any exception the temp dir is removed and nothing is left behind.
3. Ratings whose `source_policy.redistribution == "forbidden"` are excluded, listed in
   `excluded_ratings`, and produce a warning. If `source_policy` is not yet available
   (01.0/05 not landed), treat as `"unclear"` → included.
4. `warnings` = provider `caveats` (prefixed `"{rating_id}: "`) + `ValidationService`
   issues + one warning per rating whose coverage includes derived observations + the
   SQLite byte-reproducibility note. Sorted.
5. `methodology` = `Database.list_methodology_notes` for each included rating.
6. Empty selection (zero rows) → `ValidationError("release would be empty")`; no files.
7. Raw artifacts (cache files) are never copied into the bundle.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_release_bundle_contains_expected_files` | `tests/integration/test_release.py` | Integration | five files present after `demo` fetch |
| `test_release_metadata_reflects_bundle_contents` | same | Integration | manifest `coverage[].observations` sum == CSV data rows; every rating in CSV has a `provenance` entry with non-empty `parser_versions` and `acquisition_modes` |
| `test_release_is_reproducible_with_fixed_generated_at` | same | Integration | two builds → identical `checksums.txt` lines for CSV/JSON/metadata |
| `test_release_refuses_non_empty_output_without_force` | same | Integration | `StorageError` |
| `test_release_failure_leaves_no_partial_output` | same | Mock | writer raises → no `output_dir`, no temp dir |
| `test_release_excludes_forbidden_redistribution` | same | Unit | fake provider → excluded + warning |
| `test_release_never_includes_raw_artifacts` | same | Integration | bundle file list is exactly the five names |
| `test_resolve_generated_at_precedence` | same | Unit | explicit > env > now |

## Success criteria

- [ ] Task exit criterion "metadata.json alone explains every value" test-enforced.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Service owns orchestration; SQL stays in `Database`; serialization stays in `release/`.
- Never presents derived values as raw ([CLAUDE.md](/CLAUDE.md)) - `is_derived` and
  `derivation_method` columns ship unchanged.

## Out of scope

- CLI - [05](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/05-release-cli.md).
- Publishing (GitHub Releases, Zenodo) - future work.
