# Subtask 03.0/03 - Pure Retention Planner

**Task:** [03.0 - Source Archival Strategy](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 02 · **Status:** ⬜ Not started

## Goal

A side-effect-free function that, given one provider's retained artifacts and a policy,
decides which to keep and which to prune - deterministic and exhaustively unit-tested.

## Baseline

- `ArtifactRecord` and `RetentionPolicy` from subtasks 01/02.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/langrank/services/retention.py` | `RetentionPlan`, `plan_retention()` |
| Create | `tests/unit/test_retention_planner.py` | One test group per policy |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `RetentionPlan` | frozen dataclass | `policy: RetentionPolicy`, `keep: list[ArtifactRecord]`, `prune: list[ArtifactRecord]` | - | `keep ∪ prune` = input, disjoint |
| `plan_retention` | function | `(artifacts: Sequence[ArtifactRecord], policy: RetentionPolicy) -> RetentionPlan` | - | Single provider |
| `retention_bucket` | function | `(artifact: ArtifactRecord, policy: RetentionPolicy) -> tuple[str, ...]` | - | Grouping key |

## Behaviour & validators

1. `all` → keep everything.
2. `latest` → per `(url,)` bucket keep the newest by `(retrieved_at, id)`; multi-file
   sources (several URLs) keep one per URL.
3. `yearly` → per `(url, year)` bucket keep the newest, where `year` = first 4 chars of
   `edition` when present (source edition year), else `retrieved_at.year`.
4. `none` → prune everything.
5. Output lists sorted by `(retrieved_at, id)`; identical input → identical plan.
6. The planner knows nothing about files or shared paths (handled in 04).

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_plan_all_keeps_everything` | `tests/unit/test_retention_planner.py` | Unit | |
| `test_plan_latest_keeps_newest_per_url` | same | Unit | two URLs × three fetches → 2 kept |
| `test_plan_yearly_keeps_one_per_edition_year` | same | Unit | edition-based bucketing |
| `test_plan_yearly_falls_back_to_retrieved_year` | same | Unit | no edition |
| `test_plan_none_prunes_everything` | same | Unit | |
| `test_plan_is_deterministic_and_partitions_input` | same | Unit | shuffled input → same plan; keep/prune disjoint & complete |
| `test_plan_latest_tie_breaks_by_id` | same | Unit | equal timestamps |

## Success criteria

- [ ] All four policy values covered by tests (milestone testing convention).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Pure function: no I/O, no clock reads.

## Out of scope

- Deleting files - [04](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/04-archival-service.md).
