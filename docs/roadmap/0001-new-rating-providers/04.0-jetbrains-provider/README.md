# Task 04.0 - JetBrains Developer Ecosystem Provider

**Milestone:** [0001 - New Rating Providers](/docs/roadmap/0001-new-rating-providers/plan.md) ·
**Spec source:** [plan.md § Task 04.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-040---jetbrains-developer-ecosystem-provider) ·
**Category:** provider · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask | Role | Depends on | Status |
|----|---------|------|------------|--------|
| 01 | [Source note & legal/source-policy gate](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/01-source-note-and-policy-gate.md) | Security Auditor | - | ✅ Complete |
| 02 | [Survey question registry](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/02-survey-question-registry.md) | Python Expert | 01 | ✅ Complete |
| 03 | [JetBrains language aliases](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/03-jetbrains-aliases.md) | Python Expert | 01.0/02 | ✅ Complete |
| 04 | [Provider metadata & registry entry](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/04-metadata-and-registry.md) | Python Expert | 02, 03 | ✅ Complete |
| 05 | [Published-percentages dataset: fetch, parse, normalize](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/05-published-percentages.md) | Python Expert | 04 | ⬜ Not started |
| 06 | [Raw-data import: derived respondent shares](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/06-raw-data-import.md) | Python Expert | 05 | ⬜ Not started |
| 07 | [Validate: named validation codes](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/07-validate.md) | Python Expert | 05, 06 | ⬜ Not started |
| 08 | [Fixtures, golden outputs & contract tests](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/08-fixtures-and-contract-tests.md) | Testing Expert | 07, 01.0/07 | ⬜ Not started |
| 09 | [Provider documentation](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/09-docs.md) | Docs Writer | 08 | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Add a `jetbrains` provider for the annual *State of Developer Ecosystem* survey, starting with
`used_last_12_months` (the most consistently asked language question since 2017), with
`primary_language` and `planned_adoption` as separate metrics that are never merged.

## Baseline (what already exists)

- `providers/stackoverflow_survey.py` - the closest analogue (annual survey, `sample_size`,
  `population` fields populated). Reuse its approach to denominators.
- `Observation.sample_size` / `population` exist and must be filled.
- Shared helpers from Task 01.0 (`try_resolve`, `_golden.py`).

## Design notes

- **Metric IDs:** `jetbrains-used-last-12-months`, `jetbrains-primary-language`,
  `jetbrains-planned-adoption` (unit `percent`).
- **Two acquisition modes:**
  - `published` (default, `auto`) - bundled CSV `providers/data/jetbrains.csv` transcribed
    from each year's report/infographic page; values are JetBrains' **published, weighted**
    percentages → `is_derived=False`.
  - `raw-data` - `langrank import --rating jetbrains <raw.csv>` over the anonymized
    response dump JetBrains publishes (download URLs `DevEco{YEAR}/RawData.zip` verified for
    2024 and 2025 by [the source survey](/docs/research/language-ranking-sources.md); 2022 raw
    data was announced by JetBrains; 2022/2023 URLs and earlier years to be verified in subtask 01).
    The 2024 edition is licensed **CC BY-NC-SA 4.0** (non-commercial), which the legal gate must
    carry into release metadata ([0004 02.0](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md)). Percentages computed by LangRank are
    **unweighted** respondent shares → `is_derived=True`,
    `derivation_method="unweighted_respondent_share"`. They differ from published numbers
    (JetBrains reweights by region/experience) and are stored as distinct metric IDs with a
    `-raw` suffix (e.g. `jetbrains-used-last-12-months-raw`) so the two never share a
    series.
- **Question wording drift:** each metric maps per year to a question ID/wording in
  `QUESTION_REGISTRY`; wording goes into `metadata_json["question_wording"]` of every
  observation and into a `MethodologyNote` when it changes.
- Survey year vs period: the 2025 survey ran April-June 2025 and was published later;
  `period` = survey year, `source_published_at` = report publication date.

### Open questions

- Raw-data licence terms (attribution / non-commercial?) - to be settled in subtask 01; if
  redistribution is disallowed, raw files are never cached beyond the user's local cache.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] At least `jetbrains-used-last-12-months` has a validated multi-year history (2017+
      where published).
- [ ] `primary_language` and `used_last_12_months` are distinct metrics (test).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- 2025 report: <https://devecosystem-2025.jetbrains.com/>; methodology:
  <https://lp.jetbrains.com/developer-ecosystem-2025-methedology/>.
- 2024 report: <https://www.jetbrains.com/lp/devecosystem-2024/>; 2023:
  <https://www.jetbrains.com/lp/devecosystem-2023/>.
- 2022 raw data announcement: <https://blog.jetbrains.com/blog/2023/03/13/developer-ecosystem-survey-2022-discover-raw-data/>.
- Cross-source survey: [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md) (in progress).
