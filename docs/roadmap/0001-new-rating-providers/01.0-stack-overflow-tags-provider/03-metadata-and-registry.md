# Subtask 01.0/03 - Provider metadata, metrics & registry entry

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Create the `StackOverflowTagsProvider` class skeleton with complete `metadata()` (metrics,
caveats, methodology note, tag map) and register it as `stackoverflow-tags`.

## Baseline

- `src/langrank/providers/registry.py:ProviderRegistry.__init__` - hand-registered dict.
- Reference shape: `src/langrank/providers/tiobe.py:TiobeProvider.metadata`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/stackoverflow_tags.py` | Provider class, constants |
| Modify | `src/langrank/providers/registry.py` | Register `"stackoverflow-tags"` |
| Create | `tests/unit/test_stackoverflow_tags_metadata.py` | Metadata tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `StackOverflowTagsProvider.provider_id` | class attr | `str` | `"stackoverflow-tags"` | |
| `PARSER_VERSION` | module const | `str` | `"stackoverflow-tags-v1"` | |
| `TAG_TO_LANGUAGE` | module const | `dict[str, str]` | - | **Master tag** per canonical language, e.g. `"python"→"python"`, `"c++"→"c++"`, `"c#"→"c#"`, `"go"→"go"`, `"javascript"→"javascript"`, `"typescript"→"typescript"`, `"bash"→"shell"`, `"vb.net"→"vb.net"`, `"objective-c"→"objective-c"`, … (≈30) |
| `METRIC_QUESTIONS` | module const | `str` | `"stackoverflow-tags-questions"` | unit `count`, `higher_is_better=True` |
| `METRIC_SHARE` | module const | `str` | `"stackoverflow-tags-question-share"` | unit `percent` |
| `METRIC_RANK` | module const | `str` | `"stackoverflow-tags-rank"` | unit `rank`, `higher_is_better=False` |
| `metadata()` | method | `() -> ProviderMetadata` | - | `native_granularity=Granularity.MONTH`, `default_metric=METRIC_SHARE`, `homepage="https://stackoverflow.com/tags"` |

## Behaviour & validators

1. `caveats` include: "Tag activity, not usage - not comparable with stackoverflow-survey",
   "Shares can sum above 100% (multi-tag questions)", "Share denominator differs by --source",
   "Overall SO question volume declined sharply after 2022; prefer share over counts".
2. One `MethodologyNote` (`methodology_version="api-all-questions-v1"`) and one
   (`"sede-tracked-union-v1"`) describing each denominator.
3. `metric descriptions` state the denominator for the share metric explicitly.
4. Every value in `TAG_TO_LANGUAGE` resolves with
   `LanguageNormalizer().resolve(tag, rating_id="stackoverflow-tags")`.
5. `fetch/parse/normalize/validate` may raise `NotImplementedError` until subtasks 04-06.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_stackoverflow_tags_metadata_metrics` | `tests/unit/test_stackoverflow_tags_metadata.py` | Unit | Exactly the three metric IDs, units and `higher_is_better` |
| `test_stackoverflow_tags_tag_map_resolves` | `tests/unit/test_stackoverflow_tags_metadata.py` | Unit | Every tag maps to a known canonical language |
| `test_registry_contains_stackoverflow_tags` | `tests/unit/test_stackoverflow_tags_metadata.py` | Unit | `ProviderRegistry(tmp).get("stackoverflow-tags")` works |

## Success criteria

- [ ] Provider registered; `langrank ratings show stackoverflow-tags` lists three metrics.
- [ ] Tests above pass; lint/format/mypy/pytest green.

## Constraints

- No network or DB access in `__init__` or `metadata()`.
- Provider ID never reused for another metric family.

## Out of scope

- Fetching and parsing (subtasks 04-05).
