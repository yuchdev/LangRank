# 0005 - Code-Defined Canonical Language Catalog with Rating-Scoped Aliases

> **Status:** Accepted
>
> **Date:** 2026-09-29 _(recorded retroactively; global aliases since the core scaffold, rating-scoped aliases and the catalog principle since commit `6d80416`, milestone 0001)_
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

Every source names languages its own way: `cpp` / `C++`, `golang` / `Go`, `csharp` / `C#`,
Stack Overflow tag renames over time, GitHub Linguist names that include markup and config
formats, and combined categories that cannot be split - PYPL's and older JetBrains editions'
`C/C++`, IEEE's `Pascal/Delphi`. A cross-source history is only meaningful if the same
language gets the same `language_id` everywhere, and if categories that are genuinely
different never get merged just because their labels look similar.

Two failure modes have to be ruled out:

- **Silent merge:** mapping `C/C++` to `c++`, or `Visual Basic` to `vb.net`, fabricates a
  history the source never published for that language.
- **Silent drop:** an unrecognized new label disappears without anyone noticing coverage
  shrank.

## Decision

1. **The catalog is code**, in `src/langrank/normalization/languages.py`: a list of
   `CanonicalLanguage(canonical_name, display_name, aliases)` plus `RatingAlias` entries that
   apply to one `rating_id` only. `Database()` seeds both into `languages` /
   `language_aliases` on every construction ([ADR 0003](/docs/adr/0003-sqlite-storage-and-natural-key-upsert.md)),
   so the code is the source of truth and the tables are a queryable mirror.
2. **Resolution order:** rating-scoped alias first, then global alias, matched on a
   case/punctuation-insensitive key (`_normalize_key` / `Database._normalize_alias`).
3. **Combined source categories get their own canonical ID** (`c-cpp`) and are never split
   or folded into one member. The CLI explains this instead of guessing (asking PYPL for
   `c++` points the user at `c-cpp`).
4. **Catalog principle:** general-purpose and domain programming languages are tracked;
   markup, config/data formats, dialects, compilation targets and tool environments are not
   (e.g., HTML, Dockerfile, Cuda, WebAssembly, LabView). Deliberate exclusions are listed in
   per-source sets (`GITHUB_NON_LANGUAGES`, `IEEE_UNTRACKED_LABELS`) with the reason in a
   comment.
5. **Unknown labels are reported, never guessed.** A label that is neither resolvable nor a
   documented exclusion is dropped from observations, recorded in `last_unmapped`, and
   surfaced as an `unmapped_language` validation **warning** (or `UnknownLanguageError` for
   strict `resolve()` callers). `valid_from` / `valid_to` on aliases are metadata only and
   never rewrite history.

## Alternatives Considered

| Alternative                                                                                     | Pros                                                        | Cons                                                                                                                | Reason rejected                                                                                                                   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| Global aliases only                                                                             | One flat mapping; simpler                                   | Same label means different things in different sources (`c#` tag vs survey answer; combined `C/C++`); forces merges | Rejected - rating-scoped overrides are needed to keep sources honest                                                              |
| Catalog stored only in the DB, edited via CLI                                                   | Users can extend without code changes                       | Mappings diverge between installs; contract tests cannot pin them; review loses visibility                          | Deferred - user-defined aliases are a separate, proposed decision (milestone 0005 task 04.0) layered *on top of* the code catalog |
| Fuzzy / automatic matching of unknown labels                                                    | Fewer warnings; higher apparent coverage                    | Guesses produce plausible-looking wrong histories                                                                   | Rejected - `difflib` suggestions are shown to humans only, never applied                                                          |
| Split combined categories proportionally                                                        | Gives separate C and C++ lines                              | Invents numbers the source never published                                                                          | Rejected - violates [ADR 0002](/docs/adr/0002-provenance-carrying-observations.md)                                                |
| Code-defined catalog + rating-scoped aliases + documented exclusions + warn on unknown (chosen) | Deterministic, reviewable mappings; no silent merge or drop | Every new source needs catalog work; some real languages stay untracked until an alias conflict is resolved         | **Accepted**                                                                                                                      |

## Consequences

### Positive

- The same `language_id` means the same language across all ratings, so per-language
  queries across providers are well-defined (while their values remain non-comparable, see
  [ADR 0004](/docs/adr/0004-ratings-are-not-comparable-by-default.md)).
- Coverage loss is visible as warnings on every fetch.
- Mapping changes go through code review and are covered by contract tests.

### Negative

- Adding a provider almost always means editing `languages.py`, not just adding a provider
  file.
- Some legitimate languages stay untracked while a key collision is unresolved (classic
  Visual Basic vs. the global `visual basic -> vb.net` alias).
- Users cannot add a local alias without a code change until milestone 0005 task 04.0 lands.

## Validation / Rollout

- Contract tests include alias and tag-rename cases per provider and assert the
  `unmapped_language` warning for an unknown label.
- Review checklist: a new alias that maps a combined or ambiguous category onto one member
  language, or a new exclusion without a reason comment, is a blocking finding.

## Links

- **Roadmap task:** [/docs/roadmap/0001-new-rating-providers/plan.md](/docs/roadmap/0001-new-rating-providers/plan.md); follow-ups in [/docs/roadmap/0003-historical-data-quality/plan.md](/docs/roadmap/0003-historical-data-quality/plan.md) (alias validity) and [/docs/roadmap/0005-cli-and-storage-enhancements/plan.md](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) (alias management)
- **Supporting specs:** [/docs/providers.md](/docs/providers.md) (per-provider untracked labels)
- **Related ADRs:** [0002](/docs/adr/0002-provenance-carrying-observations.md), [0004](/docs/adr/0004-ratings-are-not-comparable-by-default.md)
