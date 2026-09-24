# Subtask 06.0/03 - Status service & registry tests

**Task:** [06.0 - Test Coverage Baseline](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md) ·
**Role:** Testing Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Pin `StatusService.statuses()` state derivation and `ProviderRegistry` lookup errors.

## Baseline

- `src/langrank/services/status.py:StatusService.statuses` derives `provider_state`:
  `current` (latest local observation starts with `upstream_latest_period()`), `stale`,
  `ready` (local data, no upstream period), `unknown` (no local data).
- `src/langrank/providers/registry.py:ProviderRegistry.get` raises `ProviderError` for `"all"`
  and unknown IDs.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/unit/test_status_service.py` | status tests |
| Create | `tests/unit/test_registry.py` | registry tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `_StubProvider` | test helper class | `RatingProvider`-shaped, configurable `upstream_latest_period` | - | Local to the test module; a registry built with it via monkeypatching `_providers` |

## Behaviour & validators

1. Empty DB → every provider `unknown`, `record_count == 0`.
2. After fetching `demo` → `demo` is `current` when upstream period matches, `stale` when not.
3. A provider without `upstream_latest_period` and with data → `ready`.
4. A failed fetch run populates `last_failed_fetch_at`.
5. `registry.get("all")` and `registry.get("nope")` raise `ProviderError`; `registry.all()` returns 5 providers.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_status_unknown_when_no_local_data` | `tests/unit/test_status_service.py` | Integration | rule 1 |
| `test_status_current_and_stale` | `tests/unit/test_status_service.py` | Integration | rule 2 |
| `test_status_ready_without_upstream_period` | `tests/unit/test_status_service.py` | Integration | rule 3 |
| `test_status_reports_last_failed_fetch` | `tests/unit/test_status_service.py` | Integration | rule 4 |
| `test_registry_rejects_all_and_unknown` | `tests/unit/test_registry.py` | Unit | rule 5 |
| `test_registry_lists_bootstrap_providers` | `tests/unit/test_registry.py` | Unit | rule 5 |

## Success criteria

- [ ] `src/langrank/services/status.py` ≥ 90%, `src/langrank/providers/registry.py` 100%.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Uses a `tmp_path` DB; no network.

## Out of scope

- Replacing the `hasattr` probe with capabilities - [0006 Task 01.0 subtask 04](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/04-status-service-capabilities.md).
