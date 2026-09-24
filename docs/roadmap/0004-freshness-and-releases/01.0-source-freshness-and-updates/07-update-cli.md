# Subtask 01.0/07 - `langrank update` Command

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Python Expert · **Depends on:** 06 · **Status:** ⬜ Not started

## Goal

Expose `UpdateService` as `langrank update` with human, JSON, and Markdown-summary outputs
and CI-friendly exit codes.

## Baseline

- `cli.py` pattern: commands receive `ctx.obj: AppState`, construct a service, render via
  the module-level Rich `console`; `LangRankError`s are caught in `main()`.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/cli.py` | `update` command |
| Modify | `tests/integration/test_cli.py` | CLI acceptance tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `update` | Typer command | options below | - | |
| `--provider` | option | `list[str] \| None` (repeatable) | `None` = all | |
| `--scheduled/--manual` | option | `bool` | `False` | Enforces policy + interval |
| `--online/--offline` | option | `bool` | `False` | Passed to freshness |
| `--include-unknown` | option | `bool` | `False` | |
| `--force` | option | `bool` | `False` | |
| `--dry-run` | option | `bool` | `False` | |
| `--json` | option | `bool` | `False` | Prints `UpdateSummary.to_dict()` |
| `--summary-file` | option | `Path \| None` | `None` | Writes `UpdateSummary.to_markdown()` (for CI job summaries) |

## Behaviour & validators

1. Exit codes: `0` all results non-`FAILED`; `1` at least one `FAILED`; `2` usage error
   (unknown `--provider`, via `ProviderError`).
2. Human output: one line per provider `ACTION provider_id state detail`, then any
   methodology changes and warnings.
3. `--json` output is a single JSON document (sorted keys), same shape as `to_dict()`, with
   `"update_schema_version": 1`.
4. `--summary-file` writes Markdown even when `--json` is set.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_update_cli_second_run_skips_everything` | `tests/integration/test_cli.py` | E2E | run twice on temp DB; second output has no `FETCHED` |
| `test_update_cli_json_schema` | same | E2E | parses; `update_schema_version == 1` |
| `test_update_cli_unknown_provider_exit_2` | same | E2E | exit code 2 |
| `test_update_cli_writes_summary_file` | same | E2E | Markdown file exists and names each provider |

## Success criteria

- [ ] `langrank update --help` documents every option and the policy semantics of `--scheduled`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No business logic in `cli.py` beyond argument mapping and rendering ([CLAUDE.md](/CLAUDE.md)).

## Out of scope

- Shipping an enabled CI workflow - [08](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/08-scheduled-update-docs.md) ships an example only.
