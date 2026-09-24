# Subtask 01.0/05 - Parse & normalize: counts, derived share and derived rank

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Turn an `api` JSON payload or a `sede` CSV into `SourceRecord`s and then `Observation`s:
raw monthly counts, a derived share with an explicit denominator, and a derived rank.

## Baseline

- `providers/common.py:build_observation` sets all provenance fields; `raw_record_hash` is
  the sha256 of the `SourceRecord`.
- `import` CLI command (`cli.py:import_data`) calls `parse → normalize → validate` directly
  with `FetchPayload(artifact=None, content=...)` - the `sede` path arrives this way.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/stackoverflow_tags.py` | `parse()`, `normalize()`, `_parse_api_json`, `_parse_sede_csv`, `_derive_rank` |
| Create | `tests/unit/test_stackoverflow_tags_normalize.py` | Math and provenance tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `parse` | method | `(raw: FetchPayload) -> list[SourceRecord]` | Sniffs JSON (`{`) vs CSV |
| `_parse_api_json` | function | `(content: bytes) -> list[SourceRecord]` | Emits `METRIC_QUESTIONS` and `METRIC_SHARE` records |
| `_parse_sede_csv` | function | `(content: bytes) -> list[SourceRecord]` | Expected columns: `month,tag,questions,union_total` |
| `normalize` | method | `(records: Sequence[SourceRecord]) -> list[Observation]` | Adds `METRIC_RANK` observations |
| `_derive_rank` | function | `(shares: list[Observation]) -> list[Observation]` | Dense-free competition rank per month, ties share rank |
| `self.last_unmapped` | attr | `list[str]` | Tags `try_resolve` could not map during the last `normalize` |

## Behaviour & validators

1. `SourceRecord.metadata` always has `source` (`api`/`sede`), `denominator`
   (`all_questions`/`tracked_language_union`), `denominator_count`, `tag`.
2. Questions: `value=count`, `rank=None`, `is_derived=False`.
3. Share: `value = 100 * count / denominator_count` (rounded to 4 dp),
   `is_derived=True`, `derivation_method="question_share:{denominator}"`. A zero denominator
   yields **no** share record (never 0 or NaN).
4. Rank: computed from share within one month, `is_derived=True`,
   `derivation_method="rank_by_question_share:{denominator}"`, `value=float(rank)`.
5. Period: `period_start`= first of month, `period_end` = true last day of month
   (`calendar.monthrange`, not the day-28 shortcut in `tiobe.py`), `period_label="YYYY-MM"`,
   `Granularity.MONTH`.
6. `source_document_id`: `"api:{YYYY-MM}"` or `"sede:{sha256[:12]}"`;
   `source_published_at=None`; `retrieved_at` from the artifact if present.
7. Several SEDE tags mapping to one canonical language in one month: SEDE rows are expected
   pre-deduplicated per canonical language; a duplicate `(month, language)` raises
   `NormalizationError` ("double count") rather than summing.
8. Unmapped tags are skipped and appended to `last_unmapped` (reported by subtask 06).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_share_is_derived_with_denominator_method` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | `is_derived`, method string, value math |
| `test_zero_denominator_emits_no_share` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | No share observation |
| `test_rank_ties_share_rank` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | Equal shares → equal rank, next rank skips |
| `test_period_end_is_last_day_of_month` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | Feb 2024 → 2024-02-29 |
| `test_sede_duplicate_language_month_raises` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | `NormalizationError` |
| `test_unmapped_tag_is_skipped_and_recorded` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | Absent from output, present in `last_unmapped` |
| `test_shares_may_exceed_100_in_total` | `tests/unit/test_stackoverflow_tags_normalize.py` | Unit | Multi-tag SEDE fixture sums >100, no error |

## Success criteria

- [ ] Every observation traceable to source mode, denominator, month and parser version.
- [ ] Tests above pass; lint/format/mypy/pytest green.

## Constraints

- No values interpolated for missing months; a month absent from the payload stays absent.
- Pure over inputs: no network, no DB.

## Out of scope

- Validation codes (subtask 06).
