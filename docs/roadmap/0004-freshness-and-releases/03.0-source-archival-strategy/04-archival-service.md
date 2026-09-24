# Subtask 03.0/04 - ArchivalService Pruning

**Task:** [03.0 - Source Archival Strategy](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Apply retention plans safely: delete only unreferenced files inside the cache root, mark
rows consistently, support dry-run, and report bytes freed.

## Baseline

- Multiple `raw_artifacts` rows may share one `local_path` (same sha256 re-fetched).
- `AppConfig.cache_path` is the only directory LangRank writes artifacts under.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/langrank/services/archival.py` | `ArchivalService`, `ArchivalSummary`, `ProviderArchivalResult` |
| Create | `tests/unit/test_archival_service.py` | Service tests on temp cache + DB |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `ProviderArchivalResult` | frozen dataclass | `provider_id: str`, `policy: RetentionPolicy`, `policy_source: str`, `kept: int`, `pruned: int`, `files_deleted: int`, `bytes_freed: int`, `missing: int` | - | |
| `ArchivalSummary` | frozen dataclass | `dry_run: bool`, `results: list[ProviderArchivalResult]`, `warnings: list[str]` | - | |
| `ArchivalService.__init__` | method | `(database: Database, registry: ProviderRegistry, config: AppConfig)` | - | |
| `ArchivalService.apply` | method | `(*, provider_ids: Sequence[str] = (), dry_run: bool = False) -> ArchivalSummary` | - | empty = all |

## Behaviour & validators

1. Per provider: `resolve_retention` → `plan_retention(list_artifacts(id))`.
2. Mark planned rows `pruned` **first** (transaction), then compute
   `Database.retained_paths()`, then delete each pruned row's file only if its path is not
   in the retained set. Ordering guarantees a crash never leaves a retained row pointing
   at a deleted file.
3. A path is deleted only if `Path(p).resolve()` is relative to
   `config.cache_path.resolve()`; otherwise skip and add a warning (never raise).
4. A pruned-planned file already absent → row marked `missing` instead of `pruned`,
   counted in `missing`.
5. `dry_run=True` → no DB writes, no deletions; counts reflect what would happen.
6. Idempotent: second `apply` with same config prunes nothing.
7. Observations are never touched.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_apply_latest_deletes_old_files_and_marks_rows` | `tests/unit/test_archival_service.py` | Integration | |
| `test_apply_keeps_file_shared_with_retained_row` | same | Integration | shared `local_path` survives |
| `test_apply_refuses_paths_outside_cache_root` | same | Integration | row with `/etc/...`-style path → warning, file untouched |
| `test_apply_marks_already_missing_files` | same | Integration | state `missing` |
| `test_apply_dry_run_changes_nothing` | same | Integration | DB + filesystem unchanged |
| `test_apply_is_idempotent` | same | Integration | |
| `test_apply_none_policy_keeps_rows_with_sha256` | same | Integration | rows remain with `sha256`, all `pruned` |
| `test_apply_never_touches_observations` | same | Integration | observation count unchanged |

## Success criteria

- [ ] Provenance (`sha256`, `url`, `retrieved_at`) preserved for every pruned artifact.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Service layer; providers never prune ([CLAUDE.md](/CLAUDE.md)).
- Security Auditor reviews the path-containment check (untrusted `local_path` values from an imported DB).

## Out of scope

- CLI and fetch integration - [05](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/05-cache-cli-and-fetch-hook.md).
