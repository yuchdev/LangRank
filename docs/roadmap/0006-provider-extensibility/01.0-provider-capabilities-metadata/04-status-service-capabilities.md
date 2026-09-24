# Subtask 01.0/04 - `StatusService` Reads Capabilities

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Replace the `hasattr(provider, "upstream_latest_period")` duck-typing in `StatusService` with
a `capabilities().supports_status_check` check, and gate the `import` command on
`supports_manual_import` - the plan's success criterion ("at least one generic CLI code path
reads capabilities").

## Baseline

- `src/langrank/services/status.py:StatusService.statuses` - `hasattr` branch; derives
  `provider_state` in `{"current","stale","ready","unknown"}`.
- `src/langrank/cli.py:import_data` - calls `parse/normalize/validate` for any provider.
- `src/langrank/cli.py:status` renders `ProviderStatus` into a `rich` table.

## Files

| Action | Path                                    | Purpose                                          |
|--------|-----------------------------------------|--------------------------------------------------|
| Modify | `src/langrank/services/status.py`       | Use `capabilities()`; add `supports_status_check` to `ProviderStatus` |
| Modify | `src/langrank/cli.py`                   | `import_data` refuses providers without `supports_manual_import` |
| Create | `tests/unit/test_status_service.py`     | Status branching tests with a stub provider      |

## Symbols / fields

| Symbol                                   | Kind     | Type / signature | Default | Notes |
|------------------------------------------|----------|------------------|---------|-------|
| `ProviderStatus.supports_status_check`   | field    | `bool`           | required | Rendered as `-` upstream when `False` |
| `StatusService.statuses`                 | method   | `() -> list[ProviderStatus]` | - | Signature unchanged |

## Behaviour & validators

1. `upstream_latest_period()` is called **only** when `capabilities().supports_status_check`
   is `True`; otherwise `upstream_latest_period=None` and state is `ready`/`unknown` as today.
2. A provider that declares `supports_status_check=True` but returns `None` yields state
   `unknown` (not an exception).
3. `langrank import --rating X` for a provider with `supports_manual_import=False` exits with a
   `ProviderError` message "provider X does not support manual import" (exit code 1 via `main()`).
4. No `hasattr(provider` or `provider.provider_id ==` remains in `src/langrank/services/` or
   `src/langrank/cli.py`.

## Tests

| Test function                                           | File                                  | Type | Asserts |
|---------------------------------------------------------|---------------------------------------|------|---------|
| `test_status_skips_upstream_when_not_supported`         | `tests/unit/test_status_service.py`   | Mock | Stub provider with `supports_status_check=False` whose `upstream_latest_period` raises → never called; state not `stale` |
| `test_status_marks_stale_when_upstream_newer`           | `tests/unit/test_status_service.py`   | Mock | Stub returns `"2026-01"`, local latest `2025-12-01` → `stale` |
| `test_status_unknown_when_supported_but_none`           | `tests/unit/test_status_service.py`   | Mock | Supported + `None` → `unknown` |
| `test_import_rejects_provider_without_manual_import`    | `tests/unit/test_status_service.py`   | E2E  | `CliRunner` with registry containing a stub; exit code ≠ 0, message present |

Stub registries are injected by constructing `StatusService(database, registry)` with a small
test double exposing `all()` / `get()` - no monkeypatching of built-in providers.

## Success criteria

- [ ] `grep -rn "hasattr(provider" src/langrank` returns nothing.
- [ ] `langrank status` output for built-ins unchanged (existing `tests/integration/test_cli.py` passes).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Business logic stays in `StatusService`; `cli.py` only renders.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- `status --json` and real freshness probes - [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates).
