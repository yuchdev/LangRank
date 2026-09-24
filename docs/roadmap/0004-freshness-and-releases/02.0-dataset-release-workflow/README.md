# Task 02.0 - Dataset Release Workflow

**Milestone:** [0004 - Freshness & Releases](/docs/roadmap/0004-freshness-and-releases/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-020---dataset-release-workflow) ·
**Category:** release · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                  | Role          | Depends on | Status         |
|----|--------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [Release manifest model](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/01-release-manifest-model.md) | Python Expert | -          | ⬜ Not started |
| 02 | [Release data queries](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/02-release-data-queries.md) | Python Expert | -          | ⬜ Not started |
| 03 | [Deterministic bundle writers & checksums](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/03-bundle-writers.md) | Python Expert | 01, 02     | ⬜ Not started |
| 04 | [ReleaseService assembly](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/04-release-service.md) | Python Expert | 03         | ⬜ Not started |
| 05 | [`langrank release` command](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/05-release-cli.md) | Python Expert | 04         | ⬜ Not started |
| 06 | [Release format docs](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/06-release-docs.md) | Docs Writer   | 05         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

`langrank release --since 2016 --output dist/` produces a self-describing, reproducible
bundle - `langrank-history.csv`, `langrank-history.json`, `langrank.sqlite`,
`metadata.json`, `checksums.txt` - whose `metadata.json` alone explains how every value was
produced (source, parser version, acquisition mode, methodology notes, warnings).

## Baseline (what already exists)

- `exports/csv_export.py:export_csv` / `exports/json_export.py:export_json_records` write
  `QueryRow`s, which **drop provenance** (no `parser_version`, `retrieved_at`,
  `raw_record_hash`, `is_derived`, `derivation_method`, `source_document_id`).
- `exports/json_export.py:write_metadata_sidecar` writes `version`, `generated_at`,
  `filters`, `provider_versions` - a precursor, not a release manifest.
- `Database.coverage()`, `Database.provider_versions()`, `Database.list_methodology_notes()`,
  `db/migrations.py:SCHEMA_VERSION` exist. Acquisition mode lives in
  `raw_artifacts.metadata_json` (`mode`, `provenance`) and per-row in
  `observations.metadata_json` (`provenance`).
- `dist/` is already git-ignored.

## Design notes

- **Release rows carry full provenance.** A new query returns every `observations`
  column (minus internal `id`/`fetch_run_id`), rather than reusing `QueryRow`.
- **Reproducibility = byte-identical CSV/JSON/metadata for identical DB content and
  `--generated-at`.** Rows are ordered by the natural key
  `(rating_id, metric_id, language_id, period_start, granularity)`; JSON uses
  `sort_keys=True`, `indent=2`, `\n` line endings; `generated_at` is taken from
  `--generated-at` or `SOURCE_DATE_EPOCH` when set. The SQLite file is content-reproducible
  but not guaranteed byte-identical across SQLite versions - the manifest says so, and its
  checksum is still listed.
- **Raw artifacts are never bundled.** Only normalized observations ship; providers whose
  `SourcePolicy.redistribution` (from [Task 01.0/05](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/05-scheduled-fetch-policy.md))
  is `"forbidden"` are excluded with a manifest warning. Until that subtask lands,
  `redistribution` is treated as `"unclear"` → included as derived/normalized data only,
  per the [0001 legal gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).
- **Methodology** comes from `methodology_notes` today; when
  [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking)
  extends it, the manifest's `methodology` section reads the extended table - the manifest
  field name does not change.
- **Atomic output**: write into a sibling temp dir, then rename; refuse a non-empty
  `--output` unless `--force`.

### Open questions

- Include freshness state per provider in the manifest? **Default: yes, when Task 01.0 has
  landed** (`coverage[].freshness`), else omitted - not faked.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `metadata.json` alone explains source, parser version, acquisition mode, and
      methodology for every rating in the bundle (fixture-driven test asserts it reflects
      bundle contents).
- [ ] Two runs with the same DB and `--generated-at` produce identical checksums for CSV,
      JSON, and `metadata.json`.
- [ ] `sha256sum -c checksums.txt` passes inside the bundle.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- reproducible-builds.org `SOURCE_DATE_EPOCH` specification.
- Python `sqlite3.Connection.backup`.
