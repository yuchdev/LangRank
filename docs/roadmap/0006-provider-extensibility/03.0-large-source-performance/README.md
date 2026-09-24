# Task 03.0 - Large-Source Performance Hardening

**Milestone:** [0006 - Provider Extensibility](/docs/roadmap/0006-provider-extensibility/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-030---large-source-performance-hardening) ·
**Category:** performance · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                        | Role           | Depends on | Status         |
|----|--------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Benchmark fixture generator & harness](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/01-benchmark-fixture-harness.md) | Testing Expert | -          | ⬜ Not started |
| 02 | [Batched observation upsert](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/02-batched-upsert.md)       | Python Expert  | 01         | ⬜ Not started |
| 03 | [Streaming download to cache](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/03-streaming-download.md)  | Python Expert  | 01         | ⬜ Not started |
| 04 | [Chunked CSV parsing helpers](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/04-chunked-csv-parsing.md) | Python Expert  | 01, 03     | ⬜ Not started |
| 05 | [Performance budget & regression gate](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/05-performance-budget.md) | Testing Expert | 02, 03, 04 | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Keep the largest realistic source (a Stack Overflow Developer Survey–sized CSV: ~90k rows ×
~80 columns, or a multi-year monthly tag-activity series) tractable in time and memory using
only streaming, chunking, and batched SQLite writes - no new runtime dependency and no change
to the canonical SQLite store.

## Baseline (what already exists)

- `src/langrank/util/http.py:HttpClientFactory.get_bytes` returns the full body as `bytes`
  (`response.content`); **no provider calls it today** - all five built-ins read bundled CSVs
  from `src/langrank/providers/data/`. Streaming therefore targets the Milestone 0001 providers
  that will download real artifacts.
- `src/langrank/providers/common.py:payload_from_content` takes `content: bytes`, hashes it,
  writes it to `cache_dir/<id>-<sha12>.csv|.bin`.
- `src/langrank/providers/base.py:FetchPayload(artifact, content: bytes)`; `parse()` receives
  the whole payload; providers do `raw.content.decode("utf-8").splitlines()` (two full copies).
- `src/langrank/db/repository.py:Database.upsert_observations` - one transaction, but **per row**
  a `SELECT id, raw_record_hash` followed by an `INSERT … ON CONFLICT DO UPDATE` (2N statements).
- No benchmark tests; `pyproject.toml` markers: only `integration`.

## Design notes

- **Measure first** (subtask 01): a deterministic synthetic-fixture generator + harness so every
  later subtask is justified by numbers, per plan.md "unless actual workloads justify them".
- **Protocol stays list-returning.** Per the
  [provider API stability ADR](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/01-provider-api-stability-adr.md)
  recommendation, `parse()`/`normalize()` keep returning `list` in API v1: `validate()` needs the
  full sequence for duplicate detection, and batching the *write* side removes the dominant cost.
  Streaming is applied *inside* providers (iterate CSV rows from a file handle, not from a
  decoded string) and in `FetchPayload` (a path-backed payload). If the budget in subtask 05
  can't be met with lists, that is the trigger to revisit the ADR - not before.
- **`FetchPayload` gains a path, keeps `content`.** Adding `content_path: Path | None = None` is
  an additive (minor) API change; `content` becomes lazily read for path-backed payloads via a
  helper `open_payload_text()`, so existing providers keep working unchanged.
- **No pandas.** The project doesn't depend on it; `csv` module + iterators suffice.
- **DuckDB/Spark explicitly out** (plan.md § No premature infrastructure).

### Open questions

- Budget numbers? **Default** (to be confirmed by subtask 01 measurements on CI hardware):
  200k observations upserted in ≤ 10 s and ≤ 300 MB peak RSS on the GitHub Actions
  `ubuntu-latest` runner; re-upsert of unchanged data ≤ 5 s.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Benchmark at the largest known source size completes within the documented budget
      (plan.md success criterion), using only streaming/chunking/batching.
- [ ] No new runtime dependency in `pyproject.toml` (milestone exit criterion).
- [ ] Default `uv run pytest` does **not** run benchmarks.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [SQLite `executemany` / transactions](https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.executemany).
- [httpx streaming responses](https://www.python-httpx.org/quickstart/#streaming-responses).
- [docs/source-notes/stackoverflow-survey.md](/docs/source-notes/stackoverflow-survey.md) (largest raw artifact).
