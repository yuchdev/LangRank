# Subtask 03.0/02 - Batched Observation Upsert

**Task:** [03.0 - Large-Source Performance Hardening](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Replace the per-row `SELECT` + `INSERT … ON CONFLICT` loop in `Database.upsert_observations`
with batched statements inside one transaction, preserving the exact `(inserted, updated)`
return semantics and the natural-key upsert behaviour.

## Baseline

- `src/langrank/db/repository.py:Database.upsert_observations(observations, fetch_run_id) -> tuple[int, int]`:
  for each observation, `SELECT id, raw_record_hash … WHERE <natural key>`, count inserted
  (no row) / updated (hash differs), then `INSERT … ON CONFLICT(rating_id, metric_id,
  language_id, period_start, granularity) DO UPDATE SET …`. 2N statements.
- Natural key unique constraint and `idx_observations_lookup` exist (migration 1).

## Files

| Action | Path                                     | Purpose |
|--------|------------------------------------------|---------|
| Modify | `src/langrank/db/repository.py`          | Batched implementation + `_observation_params` helper |
| Create | `tests/unit/test_upsert_batching.py`     | Semantics-preservation tests |

## Symbols / fields

| Symbol                                  | Kind     | Type / signature                                                           | Default | Notes |
|-----------------------------------------|----------|----------------------------------------------------------------------------|---------|-------|
| `Database.upsert_observations`          | method   | `(observations: Sequence[Observation], fetch_run_id: str, *, batch_size: int = 5000) -> tuple[int, int]` | `5000` | Accepts `Sequence` (was `list`) |
| `UPSERT_BATCH_SIZE`                     | constant | `int`                                                                      | `5000`  | Module-level default |
| `Database._observation_params`          | static method | `(o: Observation, fetch_run_id: str) -> tuple[object, ...]`           | -       | Single source of column order |
| `Database._existing_hashes`             | method   | `(conn, batch: Sequence[Observation]) -> dict[tuple[str, str, str, str, str], str]` | - | One query per batch |

## Behaviour & validators

1. For each batch: load existing `(natural key) → raw_record_hash` with **one** query - via a
   `TEMP TABLE` populated by `executemany` and joined, or a `VALUES`-CTE join (implementer
   chooses; document why). SQLite's host-parameter limit (32 766 on modern builds) must not be
   exceeded - batch size × key columns stays below it for the CTE approach.
2. Count `inserted` = keys absent; `updated` = keys present with different hash; unchanged rows
   count as neither (identical to today).
3. Write with `connection.executemany(<same INSERT … ON CONFLICT SQL>, params)`.
4. All batches run inside **one** transaction (whole fetch is atomic, as today); failure in any
   batch rolls back everything.
5. **Duplicate keys within the input** (same natural key twice): behaviour must match today -
   last one wins, and it is counted as inserted once and then (if hashes differ) updated once.
   Pin with a test; providers' `validate()` normally prevents this.
6. The `ON CONFLICT` column list is unchanged - no provenance field is dropped.

## Tests

| Test function                                    | File                                  | Type        | Asserts |
|--------------------------------------------------|---------------------------------------|-------------|---------|
| `test_batched_upsert_counts_match_legacy`        | `tests/unit/test_upsert_batching.py`  | Integration | Mixed insert/update/unchanged set → same `(inserted, updated)` as a reference implementation of the old loop kept in the test |
| `test_batch_boundary_sizes`                      | `tests/unit/test_upsert_batching.py`  | Integration | `batch_size` 1, 2, N-1, N, N+1 give identical DB state |
| `test_upsert_is_atomic_on_failure`               | `tests/unit/test_upsert_batching.py`  | Integration | Observation with unknown `language_id` (FK violation) in batch 2 → no rows from batch 1 persisted |
| `test_duplicate_key_in_input_last_wins`          | `tests/unit/test_upsert_batching.py`  | Integration | Rule 5 |
| `test_provenance_columns_round_trip`             | `tests/unit/test_upsert_batching.py`  | Integration | Every `Observation` field readable back unchanged |

## Success criteria

- [ ] Benchmark (`uv run pytest -m benchmark`) shows upsert-stage improvement recorded in `docs/dev/performance.md`.
- [ ] Existing `tests/integration/test_fetch_and_query.py` unchanged and green.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `Database` remains the only module containing SQL ([CLAUDE.md](/CLAUDE.md) § Storage).
- No schema migration required; if an index is added, it is a new append-only migration.

## Out of scope

- Changing `FetchService` flow (it already passes one list).
