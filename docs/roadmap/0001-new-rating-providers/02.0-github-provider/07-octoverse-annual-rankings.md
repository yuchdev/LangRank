# Subtask 02.0/07 - Octoverse annual rankings dataset

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Ship a curated CSV of Octoverse top-language ranks per edition and implement the
`octoverse` fetch/parse/normalize path, with one methodology note per ranking basis.

## Baseline

Bootstrap providers read `src/langrank/providers/data/*.csv` in `fetch()`; this variant
follows that pattern because Octoverse has no machine-readable feed.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `src/langrank/providers/data/github_octoverse.csv` | `year,rank,language,ranking_basis,source_url,published_at` |
| Modify | `src/langrank/providers/github.py` | `_fetch_octoverse`, `_parse_octoverse`, methodology notes |
| Create | `tests/unit/test_github_octoverse.py` | Parse/normalize tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `OctoverseBasis` | StrEnum | e.g. `CONTRIBUTORS="contributors"`, `MONTHLY_CONTRIBUTORS="monthly_contributors"` | Values set from the source note |
| `_parse_octoverse` | function | `(content: bytes) -> list[SourceRecord]` | `Granularity.YEAR`, `metric_id=METRIC_OCTOVERSE_RANK` |
| `--allow-chart-extraction` | CLI flag | - | **Not added**; `ProviderError` if `request.source == "octoverse-chart"` |

## Behaviour & validators

1. `rank` and `value=float(rank)` as published; `is_derived=False`.
2. `source_published_at` from `published_at`; `metadata={"ranking_basis", "provenance": "manual_curation"}`.
3. One `MethodologyNote` per distinct `ranking_basis` with `valid_from/valid_to` edition years.
4. Only ranks actually printed by GitHub are included - no gaps filled, no chart reading.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_octoverse_parse_ranks` | `tests/unit/test_github_octoverse.py` | Unit | Records, basis metadata |
| `test_octoverse_methodology_notes_per_basis` | `tests/unit/test_github_octoverse.py` | Unit | Note count = distinct bases |
| `test_octoverse_values_not_derived` | `tests/unit/test_github_octoverse.py` | Unit | `is_derived is False` |
| `test_octoverse_chart_source_refused` | `tests/unit/test_github_octoverse.py` | Unit | `ProviderError` |

## Success criteria

- [ ] Every CSV row has a `source_url` to the edition's post.
- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- Values transcribed only from text/tables published by GitHub.

## Out of scope

- Experimental chart extraction.
