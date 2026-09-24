# Subtask 02.0/05 - Innovation Graph fetch & parse

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 04, 01.0/04 · **Status:** ⬜ Not started

## Goal

Download `data/languages.csv` at a pinned commit and parse it into per-economy
`SourceRecord`s.

## Baseline

`HttpClientFactory.get_bytes/get_json`, `payload_from_content`, `load_cached_payload`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/github.py` | `_fetch_innovation_graph`, `_resolve_commit_sha`, `_parse_innovation_graph` |
| Create | `tests/unit/test_github_innovation_graph.py` | Mocked-transport + parse tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `IG_COMMITS_API` | const | `str` | `https://api.github.com/repos/github/innovationgraph/commits?path=data/languages.csv&per_page=1` |
| `IG_RAW_URL` | const | `str` | `https://raw.githubusercontent.com/github/innovationgraph/{sha}/data/languages.csv` |
| `_resolve_commit_sha` | function | `(http: HttpClientFactory) -> str` | Latest commit touching the file |
| `_fetch_innovation_graph` | method | `(request: FetchRequest) -> FetchPayload` | Artifact metadata has `commit_sha` |
| `_parse_innovation_graph` | function | `(content: bytes, *, commit_sha: str) -> list[SourceRecord]` | Required columns `num_pushers, language, iso2_code, year, quarter` |

## Behaviour & validators

1. Missing required column → `ParseError` naming it.
2. One `SourceRecord` per CSV row, `metric_id=METRIC_IG_PUSHERS`, `value=num_pushers`,
   `Granularity.QUARTER`, periods from `quarter_period`, `metadata={"iso2_code", "commit_sha", "variant"}`.
3. `since/until/years` filter rows by `period_start` after parsing.
4. `--offline` → `load_cached_payload`; `commit_sha` read from cached artifact metadata or
   from a sidecar in the cache filename.
5. Optional env `GITHUB_TOKEN` only for the commits API; never persisted.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ig_fetch_pins_commit_sha` | `tests/unit/test_github_innovation_graph.py` | Mock | Raw URL contains SHA; artifact metadata has it |
| `test_ig_parse_rows_to_records` | `tests/unit/test_github_innovation_graph.py` | Unit | Quarter periods, per-economy metadata |
| `test_ig_parse_missing_column_raises` | `tests/unit/test_github_innovation_graph.py` | Unit | `ParseError` |
| `test_ig_offline_uses_cache` | `tests/unit/test_github_innovation_graph.py` | Unit | No transport call |
| `test_github_innovation_graph_live_smoke` | `tests/integration/test_github_live.py` | Integration | `@pytest.mark.integration` |

## Success criteria

- [ ] Fetch reproducible by SHA; tests pass; lint/format/mypy/pytest green.

## Constraints

- Network only in `fetch()`.

## Out of scope

- Aggregation (subtask 06).
