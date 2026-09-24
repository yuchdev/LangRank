# Subtask 03.0/01 - Tool Contract ADR

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Architect · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Record the MCP server decision and freeze the tool/resource contract (names, parameters,
result shapes, limits) in an ADR, before any code is written.

## Baseline

- `docs/adr/` uses MADR: `template.md`, `README.md` index, and
  `0001-config-loading-via-layered-settings.md`. The `/adr-write` skill scaffolds new ADRs.

## Files

| Action | Path                                            | Purpose |
|--------|-------------------------------------------------|---------|
| Create | `docs/adr/0002-read-only-mcp-server.md`         | ADR (use `/adr-write "Read-only MCP server"`) |
| Modify | `docs/adr/README.md`                            | Index row |

## Symbols / fields

The contract the ADR must fix. All tools use `ToolAnnotations(read_only_hint=True, open_world_hint=False)`.

| Tool                  | Parameters                                                                                           | Returns (structured) |
|-----------------------|------------------------------------------------------------------------------------------------------|----------------------|
| `list_ratings`        | -                                                                                                    | `list[{rating_id, display_name, description, homepage, default_metric, native_granularity}]` |
| `list_metrics`        | `rating_id: str`                                                                                     | `list[{metric_id, display_name, unit, higher_is_better, description}]` |
| `query_observations`  | `rating_id: str`, `metric_id: str \| None`, `languages: list[str]`, `since: str \| None`, `until: str \| None`, `limit: int = 500` | `{rows: list[ObservationRow], total: int, truncated: bool, caveat: str \| None}` |
| `coverage`            | `language: str \| None`                                                                              | `list[{rating_id, earliest, latest, points, languages}]` |
| `provider_status`     | -                                                                                                    | `list[ProviderStatus]` (fields as `services/status.py:ProviderStatus`) |
| `methodology_notes`   | `rating_id: str`                                                                                     | `list[{methodology_version, valid_from, valid_to, description, source_url}]` |
| `resolve_language`    | `name: str`, `rating_id: str \| None`                                                                | `{input, language_id \| None, suggestions: list[str]}` |
| `compare_normalized`  | *(optional, Milestone 0002)* `language: str`, `ratings: list[str]`, `method: "rank_percentile"`       | `{series: [...], derivation_method, caveat}`; every point `is_derived: true` |

`ObservationRow` fields:

- `rating_id`, `metric_id`, `language_id`
- `period_start`, `period_end`, `period_label`
- `rank`, `value`, `unit`
- `source_language_name`, `source_url`, `source_document_id`
- `is_derived`, `derivation_method`
- `retrieved_at`, `source_published_at`
- `parser_version`

Resources:

| URI template                          | Returns |
|---------------------------------------|---------|
| `langrank://source-notes`             | JSON index of notes (`source_id`, `status`, `measures`, `last_verified`) |
| `langrank://source-notes/{source_id}` | Raw Markdown of `docs/source-notes/<source_id>.md` |

## Behaviour & validators

1. Limits: `limit` must be between 1 and 5000; anything outside raises a tool error.
   `languages` holds at most 50 entries.
2. Errors are MCP tool errors (`is_error=True`) with a `LangRankError` message. Never return
   a traceback.
3. The ADR's "Considered options" must include:
   - `MCPServer` (mcp 2.x) — chosen;
   - `FastMCP` 1.x;
   - the standalone `fastmcp` package;
   - no MCP server, with agents running `sqlite3` through Bash instead. That option is
     rejected: there is no read-only guarantee and no provenance contract.

## Tests

None (ADR). The contract is verified by
[subtask 06](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/06-mcp-server-tests.md).

## Success criteria

- [ ] The ADR exists with status `Accepted`, the full tool/resource table, and the limits.
- [ ] `python3 scripts/check_doc_links.py docs/adr` reports no new problems.

## Constraints

- No tool may compute a cross-rating aggregate from raw values ([CLAUDE.md](/CLAUDE.md)).

## Out of scope

- Implementation (subtasks 02-05).
