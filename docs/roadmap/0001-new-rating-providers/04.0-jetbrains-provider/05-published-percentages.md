# Subtask 04.0/05 - Published-percentages dataset: fetch, parse, normalize

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Bundle the published per-language percentages (2017+ where available) and implement the
`published` fetch/parse/normalize path.

## Baseline

Bundled-CSV pattern (`providers/data/stackoverflow_survey.csv` has
`year,language,…,sample_size,population,provenance`).

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/data/jetbrains.csv` | `year,metric,language,percent,sample_size,population,source_url,published_at` |
| Modify | `src/langrank/providers/jetbrains.py` | `fetch()`, `parse()`, `normalize()` published branch |
| Create | `tests/unit/test_jetbrains_published.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `_parse_published` | function | `(content: bytes) -> list[SourceRecord]` | `metric` column ∈ published metric IDs |

## Behaviour & validators

1. Each record's metadata has `question_wording` from `question_for(year, metric)`; a row for
   a (year, metric) the registry says was not asked → `ParseError`.
2. `is_derived=False`; `sample_size`, `population` set; `source_document_id=f"jetbrains-devecosystem-{year}"`.
3. No rank metric is stored (JetBrains publishes percentages only; a rank would be derived and
   is left to [Milestone 0002](/docs/roadmap/0002-cross-rating-analysis/plan.md)).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_jetbrains_published_parse` | `tests/unit/test_jetbrains_published.py` | Unit | Records, wording metadata |
| `test_jetbrains_published_unasked_question_raises` | `tests/unit/test_jetbrains_published.py` | Unit | `ParseError` |
| `test_jetbrains_published_sample_size_population` | `tests/unit/test_jetbrains_published.py` | Unit | Fields set |

## Success criteria

- [ ] `langrank fetch jetbrains` loads a multi-year `used_last_12_months` history.

## Constraints

- Values only as published; no fill for missing years.

## Out of scope

- Raw-data path (subtask 06).
