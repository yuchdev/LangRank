# Subtask 01.0/05 - `ratings show` Renders Capabilities

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

`langrank ratings show <id>` displays the provider's capabilities and each metric's kind, so
users (and later plugin authors) can see what a provider supports without reading its source.

## Baseline

- `src/langrank/cli.py:ratings_show` - table rows `name, description, homepage,
  native_granularity, default_metric, available_metrics, caveats`.
- `available_metrics` is a comma-joined list of IDs from `Database.list_metrics`.

## Files

| Action | Path                              | Purpose                                   |
|--------|-----------------------------------|-------------------------------------------|
| Modify | `src/langrank/cli.py`             | Add capability rows; show `id (kind)` per metric |
| Modify | `tests/integration/test_cli.py`   | Add rendering test                        |
| Modify | `docs/providers.md`               | Document the capability fields            |

## Symbols / fields

| Symbol                      | Kind     | Type / signature                                     | Default | Notes |
|-----------------------------|----------|------------------------------------------------------|---------|-------|
| `_capability_rows`          | function | `(capabilities: ProviderCapabilities) -> dict[str, str]` | - | Private helper in `cli.py`; `bool` → `yes`/`no`, tuple → comma list or `-` |

## Behaviour & validators

1. New rows, in this order after `caveats`: `historical`, `incremental`, `manual_import`,
   `status_check`, `raw_cache`, `rank`, `value`, `source_modes`.
2. `available_metrics` renders as `tiobe-rank (rank), tiobe-rating (percent)`.
3. Row keys come from `dataclasses.fields(ProviderCapabilities)` so a future field appears
   automatically (no hand-maintained list besides display order fallback).

## Tests

| Test function                                  | File                              | Type | Asserts |
|------------------------------------------------|-----------------------------------|------|---------|
| `test_ratings_show_lists_capabilities`         | `tests/integration/test_cli.py`   | E2E  | `ratings show tiobe` output contains `manual_import`, `source_modes`, `auto, official, fallback` |
| `test_ratings_show_lists_metric_kinds`         | `tests/integration/test_cli.py`   | E2E  | Output contains `pypl-share (share)` for `ratings show pypl` |

## Success criteria

- [ ] Both tests pass; `docs/providers.md` has a "Capabilities" section listing every field.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Rendering only; no logic beyond formatting in `cli.py`.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- JSON output for `ratings show` (not requested by the plan).
