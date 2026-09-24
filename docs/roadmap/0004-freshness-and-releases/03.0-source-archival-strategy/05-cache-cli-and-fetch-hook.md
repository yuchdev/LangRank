# Subtask 03.0/05 - `cache` Commands & Post-Fetch Retention

**Task:** [03.0 - Source Archival Strategy](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Add `langrank cache status` / `langrank cache prune`, apply retention automatically after
successful `fetch` (and therefore `update`), and show retention in `doctor`.

## Baseline

- `cli.py:fetch` loops providers through `FetchService.fetch`; `doctor` prints a table of
  paths/versions. Sub-apps are registered via `app.add_typer`.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/cli.py` | `cache_app` with `status`, `prune`; post-fetch hook; doctor row |
| Modify | `tests/integration/test_cli.py` | CLI tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `cache_app` | Typer sub-app | `name="cache"` | - | |
| `cache status` | command | `--json/--no-json` | `False` | per provider: policy, source, retained count/bytes, pruned count |
| `cache prune` | command | `--provider` (repeatable), `--dry-run` | all, `False` | calls `ArchivalService.apply` |
| `fetch --no-prune` | option | `bool` | `False` | skip post-fetch retention |
| `doctor` row `"retention"` | output | `str` | - | global policy + source |

## Behaviour & validators

1. After a non-dry-run `fetch` that succeeded for a provider, `ArchivalService.apply(
   provider_ids=[id])` runs unless `--no-prune`; its summary prints one line per provider.
2. Retention failures are warnings, never fail the fetch (exit code unchanged).
3. `cache status` back-fills `size_bytes` for rows where it is `NULL` and the file exists.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_fetch_applies_latest_retention` | `tests/integration/test_cli.py` | E2E | fetch twice with changed content → one retained file |
| `test_fetch_no_prune_keeps_all` | same | E2E | |
| `test_cache_prune_dry_run_output` | same | E2E | files unchanged; output lists would-prune counts |
| `test_cache_status_json` | same | E2E | valid JSON with per-provider policy |
| `test_doctor_shows_retention` | same | E2E | |

## Success criteria

- [ ] `langrank --retention none fetch demo` leaves no artifact files but keeps artifact rows.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Hook lives in the CLI/service boundary, not in `FetchService` internals or providers.

## Out of scope

- Docs - [06](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/06-retention-docs-and-repo-guard.md).
