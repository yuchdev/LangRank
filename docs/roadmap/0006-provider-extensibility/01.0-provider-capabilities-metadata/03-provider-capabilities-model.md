# Subtask 01.0/03 - `ProviderCapabilities` Model & Protocol

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Add a structured, frozen `ProviderCapabilities` record and a `capabilities()` method to the
`RatingProvider` protocol; promote `upstream_latest_period()` from a duck-typed extra to a
protocol method; implement both on all five built-in providers.

## Baseline

- `src/langrank/providers/base.py:RatingProvider` - `provider_id`, `metadata`, `fetch`,
  `parse`, `normalize`, `validate`.
- Every built-in provider defines an undeclared `upstream_latest_period() -> str` returning a
  hardcoded period (`demo` `"2026"`, `tiobe` `"2025-12"`, `pypl` `"2025-12"`, `redmonk`
  `"2025-06"`, `stackoverflow-survey` `"2025"`).
- `import` command (`cli.py:import_data`) accepts any provider - manual import is implicitly
  supported by all of them today.
- Raw caching: all providers call `providers/common.py:payload_from_content`, which caches unless
  `no_cache`.

## Files

| Action | Path                                              | Purpose                                         |
|--------|---------------------------------------------------|-------------------------------------------------|
| Modify | `src/langrank/models.py`                          | Add `ProviderCapabilities` dataclass            |
| Modify | `src/langrank/providers/base.py`                  | Add `capabilities()` and `upstream_latest_period()` to `RatingProvider` |
| Modify | `src/langrank/providers/demo.py`                  | Implement `capabilities()`                      |
| Modify | `src/langrank/providers/tiobe.py`                 | Implement `capabilities()`                      |
| Modify | `src/langrank/providers/pypl.py`                  | Implement `capabilities()`                      |
| Modify | `src/langrank/providers/redmonk.py`               | Implement `capabilities()`                      |
| Modify | `src/langrank/providers/stackoverflow_survey.py`  | Implement `capabilities()`                      |
| Modify | `src/langrank/providers/common.py`                | Add `derive_value_capabilities(metadata)` helper |
| Create | `tests/unit/test_provider_capabilities.py`        | Model + helper tests                            |

## Symbols / fields

| Symbol                                         | Kind      | Type / signature                              | Default | Notes |
|------------------------------------------------|-----------|-----------------------------------------------|---------|-------|
| `ProviderCapabilities`                         | dataclass | `@dataclass(frozen=True)`                      | -       | In `models.py` |
| `ProviderCapabilities.supports_historical`     | field     | `bool`                                         | required | Can return periods before the latest edition |
| `ProviderCapabilities.supports_incremental`    | field     | `bool`                                         | required | Honours `FetchRequest.since`/`until` to fetch less; `False` for all current built-ins (they read whole bundled CSVs) |
| `ProviderCapabilities.supports_manual_import`  | field     | `bool`                                         | required | `langrank import --rating X` accepted |
| `ProviderCapabilities.supports_status_check`   | field     | `bool`                                         | required | `upstream_latest_period()` returns non-`None` |
| `ProviderCapabilities.supports_raw_cache`      | field     | `bool`                                         | required | Produces `RawArtifact`s |
| `ProviderCapabilities.supports_rank`           | field     | `bool`                                         | required | ≥1 metric with `kind == RANK` |
| `ProviderCapabilities.supports_value`          | field     | `bool`                                         | required | ≥1 metric with `kind != RANK` |
| `ProviderCapabilities.native_granularity`      | field     | `Granularity`                                  | required | Must equal `metadata().native_granularity` |
| `ProviderCapabilities.source_modes`            | field     | `tuple[str, ...]`                              | `()`    | Accepted `FetchRequest.source` values (e.g. TIOBE `("auto","official","fallback")`); replaces ad-hoc knowledge in docs |
| `RatingProvider.capabilities`                  | method    | `() -> ProviderCapabilities`                   | -       | Protocol member |
| `RatingProvider.upstream_latest_period`        | method    | `() -> str \| None`                            | -       | Protocol member; `None` ⇔ not `supports_status_check` |
| `derive_value_capabilities`                    | function  | `(metadata: ProviderMetadata) -> tuple[bool, bool]` | - | Returns `(supports_rank, supports_value)` from metric kinds |

Built-in declarations:

| Provider               | historical | incremental | manual_import | status_check | raw_cache | rank | value | granularity | source_modes |
|------------------------|------------|-------------|---------------|--------------|-----------|------|-------|-------------|--------------|
| `demo`                 | True       | False       | True          | True         | True      | True | True  | per metadata | `()` |
| `tiobe`                | True       | False       | True          | True         | True      | True | True  | `MONTH`     | `("auto","official","fallback")` |
| `pypl`                 | True       | False       | True          | True         | True      | True | True  | per metadata | per `fetch()` |
| `redmonk`              | True       | False       | True          | True         | True      | True | False | per metadata | per `fetch()` |
| `stackoverflow-survey` | True       | False       | True          | True         | True      | True | True  | `YEAR`      | per `fetch()` |

("per metadata"/"per `fetch()`" = implementer copies the value the provider already uses; the
contract test in subtask 06 pins it.)

## Behaviour & validators

1. Providers build `supports_rank`/`supports_value` via `derive_value_capabilities(self.metadata())`
   - never hand-typed - so they cannot drift from metric kinds.
2. `native_granularity` is read from `self.metadata().native_granularity`, not repeated as a literal.
3. `capabilities()` is pure (no I/O, no DB, no network) and cheap enough to call per CLI invocation.
4. The `hasattr` check in `StatusService` is **not** removed here (that is subtask 04), but after
   this subtask mypy must accept `provider.upstream_latest_period()` directly on `RatingProvider`.

## Tests

| Test function                                         | File                                        | Type | Asserts |
|-------------------------------------------------------|---------------------------------------------|------|---------|
| `test_capabilities_is_frozen`                         | `tests/unit/test_provider_capabilities.py`  | Unit | Assigning a field raises `FrozenInstanceError` |
| `test_derive_value_capabilities_rank_only`            | `tests/unit/test_provider_capabilities.py`  | Unit | Metadata with only a RANK metric → `(True, False)` |
| `test_derive_value_capabilities_mixed`                | `tests/unit/test_provider_capabilities.py`  | Unit | RANK + SHARE → `(True, True)` |
| `test_builtin_providers_implement_capabilities`       | `tests/unit/test_provider_capabilities.py`  | Unit | For each `ProviderRegistry(tmp).all()`, `capabilities()` returns `ProviderCapabilities` |
| `test_upstream_latest_period_is_protocol_member`      | `tests/unit/test_provider_capabilities.py`  | Unit | `"upstream_latest_period" in RatingProvider.__dict__` (protocol attribute) |

## Success criteria

- [ ] `grep -n "def capabilities" src/langrank/providers/*.py` lists all five providers.
- [ ] `uv run mypy src` passes with `StatusService` still unchanged (proves protocol typing).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Frozen dataclass, full annotations, no new dependency.
- No capability-handler registry, decorators, or feature-flag system (plan.md § No premature infrastructure).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Consumers: [subtask 04](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/04-status-service-capabilities.md), [subtask 05](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/05-ratings-show-capabilities.md).
- Real (non-hardcoded) upstream freshness checks - [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates).
- Gating `import` on `supports_manual_import` - done in subtask 04 alongside the other CLI gates.
