# Subtask 03.0/04 - Query Tools

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Implement the seven always-on tools from the ADR
([subtask 01](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/01-tool-contract-adr.md))
inside `build_server()`, plus the optional `compare_normalized` tool gated on Milestone 0002.

## Baseline

- Read methods on `Database`:
  - `list_ratings`
  - `list_metrics`
  - `coverage`
  - `list_methodology_notes`
  - `alias_to_language`
  - `language_suggestions`
  - `query_observations` (from subtask 02)
- `StatusService(database, registry).statuses()` returns `list[ProviderStatus]`.
- `LanguageNormalizer.resolve` raises `UnknownLanguageError(language, suggestions)`.

## Files

| Action | Path                              | Purpose |
|--------|-----------------------------------|---------|
| Modify | `src/langrank/mcp/server.py`      | Tool registrations |
| Create | `src/langrank/mcp/schemas.py`     | `TypedDict`s / dataclasses for structured tool results |

## Symbols / fields

| Symbol                    | Kind      | Type / signature                                         | Default | Notes |
|---------------------------|-----------|----------------------------------------------------------|---------|-------|
| `READ_ONLY`               | constant  | `ToolAnnotations(read_only_hint=True, open_world_hint=False)` | - | Passed to every `@server.tool` |
| `CROSS_RATING_CAVEAT`     | constant  | `str`                                                    | "Values from different ratings measure different things and are not comparable without explicit normalization." | |
| `DEFAULT_LIMIT` / `MAX_LIMIT` | constants | `int`                                                | `500` / `5000` | |
| `MAX_LANGUAGES`           | constant  | `int`                                                    | `50` | |
| `list_ratings`            | tool      | `() -> list[RatingInfo]`                                 | - | |
| `list_metrics`            | tool      | `(rating_id: str) -> list[MetricInfo]`                   | - | Unknown rating → tool error |
| `query_observations`      | tool      | `(rating_id: str, metric_id: str \| None = None, languages: list[str] = [], since: str \| None = None, until: str \| None = None, limit: int = 500) -> ObservationPage` | - | |
| `coverage`                | tool      | `(language: str \| None = None) -> list[CoverageInfo]`   | - | Always includes `caveat` (multi-rating) |
| `provider_status`         | tool      | `() -> list[ProviderStatusInfo]`                         | - | |
| `methodology_notes`       | tool      | `(rating_id: str) -> list[MethodologyInfo]`              | - | |
| `resolve_language`        | tool      | `(name: str, rating_id: str \| None = None) -> ResolveResult` | - | |
| `compare_normalized`      | tool      | see ADR                                                  | - | Registered only if `langrank.services` exposes the Milestone 0002 normalization entry point (feature-detected at `build_server` time) |

## Behaviour & validators

1. Language names in `languages` resolve through `Database.alias_to_language`. Unknown names
   produce a tool error that includes `language_suggestions`, mirroring the CLI's
   `UnknownLanguageError` output.
2. `since`/`until` accept `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, parsed as in `cli.py:_parse_date`.
   Reuse that helper by moving it to a shared util if needed; do not duplicate it.
3. The `limit` and language-count limits from the ADR are enforced before any query runs.
4. `ObservationPage.caveat` is set only when the rows span more than one `rating_id`.
   `query_observations` is single-rating by signature, so this concerns `coverage` and
   `provider_status`.
5. `compare_normalized` output marks every point `is_derived: true` and carries
   `derivation_method` (e.g. `rank_percentile`). The raw series is never returned under the
   same key.
6. No tool exposes `top`/`top_current` while the `metric_id == "rank"` bug in
   `QueryService._apply_top_filters` is open (see the Task README baseline).
7. The module imports no `Database` write method, `FetchService`, provider `fetch`, or
   `httpx`. Verify with grep.

## Tests

Covered in [subtask 06](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/06-mcp-server-tests.md).

## Success criteria

- [ ] Seven tools are registered unconditionally. `compare_normalized` is registered only
      when its dependency exists.
- [ ] `grep -nE "upsert|create_fetch_run|FetchService|httpx|\.fetch\(" src/langrank/mcp/` has no matches.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- There is no SQL in `langrank.mcp`. All reads go through `Database`/services
  ([CLAUDE.md](/CLAUDE.md) layer rules).
- No derived value is presented as raw. There is no cross-rating shared axis or aggregate.

## Out of scope

- Resources: [subtask 05](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/05-source-note-resources.md).
