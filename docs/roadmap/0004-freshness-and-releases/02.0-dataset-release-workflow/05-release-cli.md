# Subtask 02.0/05 - `langrank release` Command

**Task:** [02.0 - Dataset Release Workflow](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Expose `ReleaseService.build` as `langrank release`.

## Baseline

- `cli.py:_parse_date(value, is_end=...)` already parses `--since`/`--until` (year or ISO date).

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/cli.py` | `release` command |
| Modify | `tests/integration/test_cli.py` | CLI acceptance tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `release` | Typer command | options below | - | |
| `--output` | option | `Path` | `Path("dist")` | |
| `--since` / `--until` | option | `str \| None` | `None` | via `_parse_date` |
| `--ratings` | option | `str \| None` (comma list) | `None` = all | unknown ID → exit 2 |
| `--generated-at` | option | `str \| None` (ISO 8601) | `None` | reproducible builds |
| `--force` | option | `bool` | `False` | |

## Behaviour & validators

1. On success prints the output path, row count, and each file with its sha256 prefix.
2. Prints manifest warnings after the file list (yellow), exit `0`.
3. `StorageError`/`ValidationError` propagate to `main()` → exit `1` with message.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_release_cli_writes_bundle` | `tests/integration/test_cli.py` | E2E | `fetch demo` then `release --output tmp/rel` → five files |
| `test_release_cli_unknown_rating_exit_2` | same | E2E | |
| `test_release_cli_generated_at_is_used` | same | E2E | `metadata.json.generated_at` equals flag value |

## Success criteria

- [ ] `langrank release --help` matches the plan's example invocation.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Thin CLI; no assembly logic here ([CLAUDE.md](/CLAUDE.md)).

## Out of scope

- Format documentation - [06](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/06-release-docs.md).
