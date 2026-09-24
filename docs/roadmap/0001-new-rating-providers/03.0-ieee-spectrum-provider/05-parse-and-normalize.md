# Subtask 03.0/05 - Parse & normalize per profile

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Parse edition rows into a rank and a score `SourceRecord` per (year, profile, language) and
normalize with full provenance.

## Baseline

`build_observation`; `try_resolve`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/ieee_spectrum.py` | `parse()`, `normalize()` |
| Create | `tests/unit/test_ieee_spectrum_normalize.py` | Tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `parse` | method | `(raw: FetchPayload) -> list[SourceRecord]` | Unknown `profile` → `ParseError` |
| `normalize` | method | `(records: Sequence[SourceRecord]) -> list[Observation]` | |

## Behaviour & validators

1. Period: `date(year,1,1)`..`date(year,12,31)`, label `"YYYY"`, `Granularity.YEAR`;
   `source_published_at` from `published_at`.
2. `source_document_id=f"ieee-tpl-{year}"`; `metadata={"profile", "methodology_version", "provenance"}`.
3. `is_derived=False` for both rank and score (published values).
4. Empty `score` cell → no score record (rank still stored).
5. Unmapped labels → `last_unmapped`, skipped.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ieee_parse_emits_rank_and_score_per_profile` | `tests/unit/test_ieee_spectrum_normalize.py` | Unit | Metric IDs per profile |
| `test_ieee_missing_score_not_fabricated` | `tests/unit/test_ieee_spectrum_normalize.py` | Unit | No score observation |
| `test_ieee_unknown_profile_raises` | `tests/unit/test_ieee_spectrum_normalize.py` | Unit | `ParseError` |
| `test_ieee_provenance_fields` | `tests/unit/test_ieee_spectrum_normalize.py` | Unit | doc id, published_at, methodology metadata |

## Success criteria

- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- Pure; no interpolation between editions.

## Out of scope

- Validation (subtask 06).
