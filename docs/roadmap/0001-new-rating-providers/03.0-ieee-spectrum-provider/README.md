# Task 03.0 - IEEE Spectrum Provider

**Milestone:** [0001 - New Rating Providers](/docs/roadmap/0001-new-rating-providers/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-030---ieee-spectrum-provider) ·
**Category:** provider · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask | Role | Depends on | Status |
|----|---------|------|------------|--------|
| 01 | [Source note & legal/source-policy gate](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/01-source-note-and-policy-gate.md) | Security Auditor | - | ✅ Complete |
| 02 | [IEEE language aliases](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/02-ieee-aliases.md) | Python Expert | 01.0/02 | ✅ Complete |
| 03 | [Provider metadata, profiles & registry entry](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/03-metadata-profiles-and-registry.md) | Python Expert | 02 | ✅ Complete |
| 04 | [Curated edition dataset & fetch/import path](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/04-curated-dataset-and-fetch.md) | Python Expert | 01, 03 | ✅ Complete |
| 05 | [Parse & normalize per profile](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/05-parse-and-normalize.md) | Python Expert | 04 | ✅ Complete (rank derived from published scores - see status.md) |
| 06 | [Validate: named validation codes](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/06-validate.md) | Python Expert | 05 | ✅ Complete |
| 07 | [Fixtures, golden outputs & contract tests](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/07-fixtures-and-contract-tests.md) | Testing Expert | 06, 01.0/07 | ⬜ Not started |
| 08 | [Provider documentation](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/08-docs.md) | Docs Writer | 07 | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Add an `ieee-spectrum` provider that stores IEEE Spectrum's annual *Top Programming
Languages* rank and score **per ranking profile**, each profile as its own metric so a query
never mixes profiles into one series.

## Baseline (what already exists)

- Bundled-CSV provider pattern (`providers/tiobe.py`, `providers/data/*.csv`).
- `MethodologyNote` model and `methodology_notes` table (migration 2) already exist -
  edition-level methodology changes are recorded there now, ahead of
  [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking).
- Shared helpers from Task 01.0 (`try_resolve`, `_golden.py`).

## Design notes

- **Profiles (verified for 2022-2025):** `spectrum` (default, IEEE-member weighting), `jobs`
  (employer demand), `trending` (zeitgeist). Pre-2022 interactive editions had presets such
  as "Trending", "Jobs" and "Open"; which pre-2022 profiles are importable is decided in
  subtask 01 and recorded per edition. plan.md's `default` profile is named `spectrum`
  here to match IEEE's own label.
- **Metric IDs:** `ieee-spectrum-{profile}-rank` and `ieee-spectrum-{profile}-score`
  (e.g. `ieee-spectrum-jobs-rank`). `score` is IEEE's published relative score (top
  language = 100) - raw, not derived.
- **Acquisition:** IEEE publishes no downloadable dataset; the interactive app and articles
  are the only sources, and since 2025 IEEE itself gathers the data manually (API
  terminations). Acquisition therefore = curated bundled CSV
  `providers/data/ieee_spectrum.csv` (provenance `manual_transcription`) plus the existing
  `langrank import --rating ieee-spectrum <csv>` path for new editions. No scraping of the
  interactive app.
- **Methodology versions:** the metric set and weights change between editions (e.g. 11
  metrics from 8 sources in earlier editions; 7 metrics in 2025; profile redesign in 2022).
  One `MethodologyNote` per edition; parsers are versioned only if the CSV format changes.
- Coverage: only ranks IEEE publishes in the article/app; if a profile shows only a top-N,
  ranks beyond N stay missing.

### Open questions

- Transcribe full list (~60 languages) or top 20 per profile? Proposed default: full list
  where the app shows it; otherwise the published top-N, noted in metadata `coverage`.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Each profile round-trips `fetch → parse → normalize → validate` as its own metric pair.
- [ ] Querying one profile never returns another profile's rows (test).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- 2025 edition: <https://spectrum.ieee.org/top-programming-languages-2025>; methodology:
  <https://spectrum.ieee.org/top-programming-languages-methodology-2025>.
- 2024 methodology: <https://spectrum.ieee.org/top-programming-languages-methodology-2024>.
- Earlier interactive editions, e.g. 2021: <https://spectrum.ieee.org/top-programming-languages-interactive-2021/>, 2019: <https://spectrum.ieee.org/the-top-programming-languages-2019>.
- Cross-source survey: [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md) (in progress).
