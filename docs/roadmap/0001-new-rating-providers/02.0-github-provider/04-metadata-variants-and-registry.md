# Subtask 02.0/04 - Provider metadata, variants & registry entry

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 02, 03 · **Status:** ⬜ Not started

## Goal

Create `GitHubProvider` with metadata for both variants, `--source` dispatch and registry
entry `github`.

## Baseline

`FetchRequest.source` is a free string; `TiobeProvider.fetch` shows the `mode` pattern.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/github.py` | Provider class, constants, dispatch |
| Modify | `src/langrank/providers/registry.py` | Register `"github"` |
| Create | `tests/unit/test_github_metadata.py` | Metadata / dispatch tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `GitHubProvider.provider_id` | class attr | `str` | `"github"` | |
| `GitHubSource` | StrEnum | `OCTOVERSE="octoverse"`, `INNOVATION_GRAPH="innovation-graph"` | - | |
| `PARSER_VERSION` | const | `str` | `"github-v1"` | |
| `METRIC_OCTOVERSE_RANK` | const | `str` | `"github-octoverse-rank"` | unit `rank`, lower better |
| `METRIC_IG_PUSHERS` | const | `str` | `"github-innovation-graph-pushers"` | unit `count` |
| `METRIC_IG_SHARE` | const | `str` | `"github-innovation-graph-share"` | unit `percent` |
| `METRIC_IG_RANK` | const | `str` | `"github-innovation-graph-rank"` | unit `rank` |
| `_resolve_source` | function | `(value: str \| None) -> GitHubSource` | `auto`→`INNOVATION_GRAPH` | `ProviderError` on unknown |

## Behaviour & validators

1. `native_granularity=Granularity.QUARTER`, `default_metric=METRIC_IG_SHARE`.
2. Caveats: "Not RedMonk's GitHub component", "Innovation Graph global values are sums of
   per-economy cells with ≥100 developers (undercount)", "Octoverse ranking basis changes
   between editions", "No chart-derived values".
3. `fetch/parse` dispatch on the source; payload metadata carries `"variant"`.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_github_metadata_metrics` | `tests/unit/test_github_metadata.py` | Unit | Four metric IDs, units |
| `test_github_resolve_source` | `tests/unit/test_github_metadata.py` | Unit | auto/None/octoverse/innovation-graph + error |
| `test_registry_contains_github` | `tests/unit/test_github_metadata.py` | Unit | `get("github")` |

## Success criteria

- [ ] `langrank ratings show github` shows both variants' metrics and caveats.

## Constraints

- No I/O in `__init__`/`metadata()`.

## Out of scope

- Per-variant fetch logic (subtasks 05, 07).
