# Subtask 04.0/04 - Provider metadata & registry entry

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 02, 03 · **Status:** ⬜ Not started

## Goal

Create `JetBrainsProvider` with published and raw metric families, methodology notes from
question-wording changes, and register `jetbrains`.

## Baseline

`StackOverflowSurveyProvider.metadata` pattern.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/jetbrains.py` | Provider |
| Modify | `src/langrank/providers/registry.py` | Register |
| Create | `tests/unit/test_jetbrains_metadata.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `JetBrainsProvider.provider_id` | class attr | `str` | `"jetbrains"` | |
| `PUBLISHED_METRICS` | const | `tuple[str, ...]` | 3 IDs | unit `percent` |
| `RAW_METRICS` | const | `tuple[str, ...]` | same with `-raw` suffix | derived |
| `JetBrainsSource` | StrEnum | `PUBLISHED="published"`, `RAW_DATA="raw-data"` | `auto`→`PUBLISHED` | |
| `PARSER_VERSION` | const | `str` | `"jetbrains-v1"` | |

## Behaviour & validators

1. `default_metric="jetbrains-used-last-12-months"`, `Granularity.YEAR`.
2. Caveats: "Self-reported survey - not comparable with activity metrics",
   "Published values are weighted; -raw values are unweighted respondent shares",
   "primary_language and used_last_12_months answer different questions".
3. `methodology_notes` built from `wording_changes()` for each metric.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_jetbrains_metadata_metric_families` | `tests/unit/test_jetbrains_metadata.py` | Unit | 6 IDs, disjoint families |
| `test_jetbrains_methodology_notes_from_wording` | `tests/unit/test_jetbrains_metadata.py` | Unit | Notes per change |
| `test_registry_contains_jetbrains` | `tests/unit/test_jetbrains_metadata.py` | Unit | `get("jetbrains")` |

## Success criteria

- [ ] `langrank ratings show jetbrains` lists both families.

## Constraints

- No I/O in `metadata()`.

## Out of scope

- Data paths.
