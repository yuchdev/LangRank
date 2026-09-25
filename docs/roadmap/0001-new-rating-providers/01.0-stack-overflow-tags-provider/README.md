# Task 01.0 - Stack Overflow Tags Provider

**Milestone:** [0001 - New Rating Providers](/docs/roadmap/0001-new-rating-providers/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-010---stack-overflow-tags-provider) ·
**Category:** provider · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask | Role | Depends on | Status |
|----|---------|------|------------|--------|
| 01 | [Source note & legal/source-policy gate](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/01-source-note-and-policy-gate.md) | Security Auditor | - | ✅ Complete |
| 02 | [Language catalog expansion & rating-scoped aliases](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/02-rating-scoped-aliases.md) | Python Expert | - | ✅ Complete (`visual-basic` deferred - key collides with `vb.net` alias; see status.md) |
| 03 | [Provider metadata, metrics & registry entry](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/03-metadata-and-registry.md) | Python Expert | 02 | ✅ Complete |
| 04 | [Fetch: Stack Exchange API client, SEDE import & offline cache](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/04-fetch-api-and-offline-cache.md) | Python Expert | 03 | ✅ Complete |
| 05 | [Parse & normalize: counts, derived share and derived rank](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/05-parse-and-normalize.md) | Python Expert | 04 | ✅ Complete |
| 06 | [Validate: named validation codes](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/06-validate.md) | Python Expert | 05 | ✅ Complete |
| 07 | [Fixtures, golden outputs & contract tests](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/07-fixtures-and-contract-tests.md) | Testing Expert | 06 | ✅ Complete |
| 08 | [Provider documentation](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/08-docs.md) | Docs Writer | 07 | ✅ Complete |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Add a `stackoverflow-tags` provider that records **monthly question activity per language
tag**: raw `questions` counts plus a derived `question_share` (preferred for long-term
comparison because total Stack Overflow volume has fallen sharply since ~2022) and a derived
`rank`. Tag activity is a different measure from the existing `stackoverflow-survey` provider
(self-reported usage) and the two must never be conflated.

## Baseline (what already exists)

- `src/langrank/providers/stackoverflow_survey.py:StackOverflowSurveyProvider` - survey
  provider; its IDs (`stackoverflow-survey`, `worked_with_percent`) must not be reused.
- `src/langrank/util/http.py:HttpClientFactory.get_bytes` - retrying GET; **currently unused**:
  every bootstrap provider's `fetch()` reads a bundled CSV from `src/langrank/providers/data/`.
  This is the first provider that performs a real network fetch.
- `src/langrank/providers/common.py:payload_from_content` writes the cache but nothing reads
  it back; `FetchRequest.offline` is accepted but ignored by every provider.
- `src/langrank/normalization/languages.py:LanguageNormalizer` - only 12 canonical languages
  (no TypeScript, Kotlin, Swift, PHP, Ruby, …) and every alias is global (`rating_id=""`),
  although `language_aliases.rating_id` and `LanguageAlias.valid_from/valid_to` already exist
  in the schema/model. `resolve()` raises `UnknownLanguageError` on any unknown name, which
  aborts a whole fetch.
- Metric IDs are provider-prefixed (`tiobe-rank`, `pypl-rank`); bare `metric_id == "rank"`
  comparisons in `QueryService._apply_top_filters`, `Database.validation_queries`
  (`invalid_ranks`) and `PlotService` are fixed by
  [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata) -
  this task follows the prefixed convention and does not duplicate that fix.

## Design notes

- **Metric IDs** (prefixed, per the existing convention): `stackoverflow-tags-questions`
  (unit `count`, raw), `stackoverflow-tags-question-share` (unit `percent`, derived),
  `stackoverflow-tags-rank` (unit `rank`, derived - SO publishes no rank).
- **Acquisition modes** (`--source`):
  - `api` (default for `auto`) - Stack Exchange API v2.3,
    `GET https://api.stackexchange.com/2.3/questions?site=stackoverflow&tagged={tag}&fromdate={epoch}&todate={epoch}&filter=total`
    returns `{"total": N}` - one request per tag per month. Unauthenticated quota is
    ~300 requests/day per IP; an app `key` (env `LANGRANK_STACKEXCHANGE_KEY`, optional)
    raises it to 10,000/day. Honour the `backoff` field in responses. 10 years × 12 months ×
    ~30 tags ≈ 3,600 requests → a full backfill needs a key or several days; incremental
    monthly updates are ~30 requests.
  - `sede` - manual import of a CSV exported from Stack Exchange Data Explorer
    (`data.stackexchange.com`), the only practical way to get the **deduplicated union**
    denominator. Run via `langrank import --rating stackoverflow-tags <csv>`.
- **Denominator correction to plan.md:** plan.md recommends "questions carrying at least one
  tracked language tag" as the default denominator. The API cannot compute that union
  (`tagged=a;b` is AND, not OR), so:
  - `api` mode uses `all_questions` (a `filter=total` call with no tag) as the denominator,
    `derivation_method="question_share:all_questions"`;
  - `sede` mode uses `tracked_language_union`,
    `derivation_method="question_share:tracked_language_union"`.
  The two are **different metrics semantically**; the denominator is stored in
  `metadata_json["denominator"]` and the two modes must not be mixed in one series
  (validation code `mixed_denominator`).
- Shares may sum above 100 % across languages (multi-tag questions). This is documented, not
  a validation error.
- **Rename/synonym tags:** SO merges synonyms server-side (`cpp` → `c++`, `golang` → `go`), so
  querying the master tag returns historical questions. Aliases still matter for SEDE exports
  and for mapping tags such as `c#` / `csharp`, `objective-c`, `vb.net`, `bash`/`shell`.
  One canonical language may map to several tags (`shell` ← `bash`, `shell`, `sh`); the
  provider must count each question once per canonical language - only possible exactly in
  `sede` mode; `api` mode queries **one master tag per language** (table in subtask 03).
- **Month boundaries:** `fromdate` = first second of the month UTC, `todate` = last second;
  the current, incomplete month is never fetched.
- **Shared helpers owned here:** rating-scoped aliases / `try_resolve` (subtask 02) and the
  offline cache reader `load_cached_payload` (subtask 04) and golden-output helper (subtask
  07) are reused by Tasks 02.0-04.0. Whichever task starts first lands them.

### Open questions

- Should `api` mode also persist `stackoverflow-tags-answers`? Proposed default: no - out of
  scope for this milestone.
- Tracked tag set size: proposed default = every canonical language that has a tag mapping
  in subtask 03 (≈30).

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `langrank fetch stackoverflow-tags` produces `stackoverflow-tags-question-share`
      observations whose `derivation_method` names the denominator, and the denominator is
      documented in `docs/source-notes/stackoverflow-tags.md`.
- [ ] Contract tests cover multi-tag questions (SEDE fixture) and tag rename aliases.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- Stack Exchange API v2.3 docs: <https://api.stackexchange.com/docs/questions>,
  throttling: <https://api.stackexchange.com/docs/throttle>, `filter=total`:
  <https://api.stackexchange.com/docs/filters>.
- Stack Exchange Data Explorer: <https://data.stackexchange.com/stackoverflow/query/new>.
- Data-dump access change (July 2024: dumps moved behind login, downloader must agree to
  non-LLM-training use): <https://devclass.com/2024/07/30/stack-exchange-restricts-access-to-dump-of-user-contributed-data-as-critics-complain-license-permits-reuse-for-any-purpose/>.
  Consequence: the data dump is **not** used as an automated source.
- User content is CC BY-SA 4.0 (attribution required); aggregate counts are facts, but
  attribution is still recorded in provider metadata.
- Cross-source survey: [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md) (in progress).
