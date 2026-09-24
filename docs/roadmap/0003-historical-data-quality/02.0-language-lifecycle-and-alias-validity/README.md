# Task 02.0 - Language Births, Renames & Alias Validity Ranges

**Milestone:** [0003 - Historical Data Quality](/docs/roadmap/0003-historical-data-quality/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-020---language-births-renames--alias-validity-ranges) ·
**Category:** data-model · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                                  | Role          | Depends on | Status         |
|----|----------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [ADR: one alias-resolution rule set](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/01-adr-single-resolution-path.md)                     | Architect     | -          | ⬜ Not started |
| 02 | [Lifecycle catalog & schema migration](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/02-lifecycle-catalog-and-migration.md)             | Python Expert | 01         | ⬜ Not started |
| 03 | [Date- and rating-aware alias resolution](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/03-date-aware-resolution.md)                     | Python Expert | 02         | ⬜ Not started |
| 04 | [Providers adopt dated resolution](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/04-provider-adoption.md)                                | Python Expert | 03         | ⬜ Not started |
| 05 | [No-zero-fill guarantee & lifecycle validation](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/05-no-zero-fill-guarantee.md)              | Testing Expert| 03         | ⬜ Not started |
| 06 | [Document lifecycle & alias validity](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/06-docs.md)                                          | Docs Writer   | 04, 05     | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

A language that did not exist yet shows a real gap, never zeros; a source label that was
renamed resolves correctly for the periods each label was in effect; the original source
label is always preserved in `observations.source_language_name`.

## Baseline (what already exists)

- Schema already has `language_aliases.valid_from/valid_to/notes` and a per-rating
  `rating_id` column (`''` = global); `models.py:LanguageAlias` mirrors it.
- `normalization/languages.py:LanguageNormalizer` is a hard-coded catalog of 12 languages
  with **global-only, undated** aliases; `aliases()` always emits `rating_id=""` and no dates.
- **Two resolution paths:** providers call `LanguageNormalizer.resolve(value)` in
  `normalize()` (pure, no DB); the CLI (`languages show`, `coverage`, `_language_ids`) calls
  `Database.alias_to_language(source_name, rating_id)`, which ignores `valid_from/valid_to`.
  Both use the same key-normalization function, duplicated
  (`LanguageNormalizer._normalize_key` vs `Database._normalize_alias`).
- `observations.source_language_name` is already stored by `build_observation` (the
  original label is preserved) — this task relies on, and tests, that.
- `languages` has no birth/retirement data.
- Queries never zero-fill today (`query_rows` returns only stored rows); there is no test
  pinning that.

## Design notes

- **The catalog is the single source of truth; resolution rules are one pure function.**
  Providers must stay DB-free ([CLAUDE.md](/CLAUDE.md) § Conventions), so the rules live in
  `normalization/` and `Database.alias_to_language` delegates to the same rule function over
  rows it loads. A parity test enforces identical results (ADR, subtask 01).
- **Precedence:** rating-specific alias valid on the date → global alias valid on the date →
  canonical/display name. Undated aliases are valid for all dates.
- **Lifecycle:** `CanonicalLanguage.introduced` / `retired` (`date | None`) seeded into new
  `languages.introduced` / `languages.retired` columns. These are informational for
  validation and the quality dashboard; they never filter or fill query results.
- **No zero-fill:** absence is represented by absence of rows. A regression test pins query,
  CSV/JSON export, and plot behaviour.
- Overlap with [Milestone 0005 Task 04.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-040---alias-management-commands)
  (alias CLI): this task only adds the `on_date` parameter and validity columns to existing
  output; new alias commands stay in 0005.

### Open questions

- What if a label is only valid outside the observation's date? *Default: resolution
  fails with `UnknownLanguageError` whose message names the validity range — the provider's
  fetch fails loudly rather than mapping silently.*
- Where do birth dates come from? *Default: first public release year, cited in a code
  comment; `None` when unknown (no guessing).*

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] A language added mid-range shows no observations before its birth, not zeros (plan.md).
- [ ] A renamed alias is queryable under the old and new label for its effective periods (plan.md).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/data-model.md](/docs/data-model.md), [docs/providers.md](/docs/providers.md)
- [Milestone 0001 plan](/docs/roadmap/0001-new-rating-providers/plan.md) — tag renames for `stackoverflow-tags` are the first real consumer.
