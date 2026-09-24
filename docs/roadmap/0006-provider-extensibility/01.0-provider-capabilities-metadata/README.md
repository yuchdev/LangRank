# Task 01.0 - Provider Capabilities Metadata

**Milestone:** [0006 - Provider Extensibility](/docs/roadmap/0006-provider-extensibility/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata) ·
**Category:** provider-infra · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                             | Role           | Depends on | Status         |
|----|-------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Metric kind metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/01-metric-kind-metadata.md)     | Python Expert  | -          | ⬜ Not started |
| 02 | [Metric-role lookups replace bare `"rank"`](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/02-metric-role-lookups.md) | Python Expert  | 01         | ⬜ Not started |
| 03 | [`ProviderCapabilities` model & protocol](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/03-provider-capabilities-model.md) | Python Expert  | 01         | ⬜ Not started |
| 04 | [`StatusService` reads capabilities](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/04-status-service-capabilities.md) | Python Expert  | 03         | ⬜ Not started |
| 05 | [`ratings show` renders capabilities](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/05-ratings-show-capabilities.md) | Python Expert  | 03         | ⬜ Not started |
| 06 | [Capabilities ↔ metadata contract test](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/06-capabilities-contract-test.md) | Testing Expert | 03, 04     | ⬜ Not started |
| 07 | [Derived-rank provenance](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/07-derived-rank-provenance.md) | Python Expert  | 01         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Make generic code (status, query, validation, plotting, CLI rendering) work from what a
provider *declares* rather than from its ID or from string conventions. Two kinds of
declaration are added: a **metric kind** on every `MetricDefinition` (is this metric a rank,
a share, a score, a count, a percentage?) and a **`ProviderCapabilities`** record on every
provider. Both are prerequisites for
[Task 02.0](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md):
a third-party provider cannot be special-cased by ID in core code, so core code must stop
doing that for built-ins first.

## Baseline (what already exists)

- `src/langrank/models.py:MetricDefinition` - `id`, `rating_id`, `display_name`, `unit`,
  `higher_is_better`, `description`. No notion of metric kind.
- `src/langrank/models.py:ProviderMetadata.native_granularity` - already declared per provider;
  capabilities must agree with it, not duplicate it inconsistently.
- `src/langrank/providers/base.py:RatingProvider` - five methods; no capabilities.
- **Latent bug (fixed by subtask 02):** production providers use provider-prefixed metric IDs
  (`tiobe-rank`, `pypl-rank`, `redmonk-rank`, `stackoverflow-survey-rank`, `tiobe-rating`,
  `pypl-share`, `worked_with_percent`); only `demo` uses bare `rank`/`rating`. Yet:
  - `src/langrank/services/query.py:QueryService._apply_top_filters` filters on
    `row.metric_id == "rank"` → `--top`/`--top-current` select nothing for real providers.
  - `src/langrank/db/repository.py:Database.validation_queries` `invalid_ranks` uses
    `WHERE metric_id = 'rank'` → never fires for real providers.
  - `src/langrank/plotting/service.py:PlotService.plot` inverts the axis only when
    `metric_id == "rank"` → `redmonk-rank` plots upside-down.
  - `src/langrank/cli.py:plot` defaults `--metric` to `"rating"`, which exists only for `demo`.
- `src/langrank/services/status.py:StatusService.statuses` uses
  `hasattr(provider, "upstream_latest_period")` - the exact ID/duck-type special-casing this
  task removes. Every provider currently hardcodes `upstream_latest_period()` (e.g. TIOBE
  returns `"2025-12"`).
- `src/langrank/cli.py:ratings_show` renders metadata fields but not capabilities.

## Design notes

- **Metric kind before capabilities.** `supports_rank`/`supports_value` are *derived* from the
  metric kinds a provider declares, so `MetricKind` lands first (subtask 01). Capabilities that
  can be derived are validated against metadata by the contract test (subtask 06) rather than
  trusted blindly.
- **`MetricKind` values:** `rank`, `share`, `score`, `count`, `percent`. `share` = a fraction of
  a denominator (PYPL share, SO tag question share); `percent` = survey percentage of respondents
  (`worked_with_percent`) or an index rating expressed in percent (`tiobe-rating`) - distinguished
  because shares may sum to ~100% across languages and survey percentages need not. `score` =
  composite index value (IEEE Spectrum); `count` = absolute counts (SO `questions`).
- **Backfill rule for existing DB rows** (migration in subtask 01): `unit = 'rank'` → `rank`;
  `unit = 'percent'` → `percent`; `unit IN ('share','fraction')` → `share`; anything else →
  `score`. New metadata upserts overwrite the backfilled value with the provider's declaration.
- **Optional behaviour stays on the protocol, gated by capability.** Rather than keeping
  `upstream_latest_period` as a duck-typed extra, it becomes a protocol method
  `upstream_latest_period() -> str | None`; providers without `supports_status_check` return
  `None`. `typing.Protocol` cannot express optional methods, and `hasattr` checks are
  exactly what plugins would break.
- **Not a plugin framework.** Per plan.md § No premature infrastructure: a frozen dataclass and
  one method, nothing more (no registry of capability handlers, no feature flags).

### Open questions

- Should `default_metric` resolution for `plot`/`query` move into a service helper? **Default:**
  yes - `QueryService.default_metric_id(rating_id)` in subtask 02, reused by the CLI.
- Should `MetricKind` be exposed in exports? **Default:** yes in the JSON metadata sidecar only
  (`exports/json_export.py:write_metadata_sidecar`); CSV column layout unchanged.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] At least one generic CLI path (`status`) reads capabilities off the provider instance -
      no `hasattr(provider, ...)` or `provider_id == ...` branch remains in `services/` or `cli.py`
      (verified by `grep -rn "hasattr(provider\|provider_id ==" src/langrank/services src/langrank/cli.py`).
- [ ] No bare `"rank"`/`'rank'` metric-ID literal remains in `services/`, `db/repository.py`,
      `plotting/`, or `cli.py`; `--top`, `invalid_ranks`, and rank-axis inversion work for
      `tiobe`, `pypl`, `redmonk`, `stackoverflow-survey`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [CLAUDE.md](/CLAUDE.md) § Architecture (provider protocol, registry) and § Conventions.
- [docs/data-model.md](/docs/data-model.md), [docs/providers.md](/docs/providers.md).
- [Milestone 0006 plan § Stabilize contracts](/docs/roadmap/0006-provider-extensibility/plan.md#stabilize-contracts-before-exposing-them-externally).
