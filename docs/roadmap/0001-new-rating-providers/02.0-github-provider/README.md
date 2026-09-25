# Task 02.0 - GitHub Provider

**Milestone:** [0001 - New Rating Providers](/docs/roadmap/0001-new-rating-providers/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-020---github-provider) ·
**Category:** provider · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask | Role | Depends on | Status |
|----|---------|------|------------|--------|
| 01 | [Source note & legal/source-policy gate](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/01-source-note-and-policy-gate.md) | Security Auditor | - | ⬜ Not started |
| 02 | [Quarterly granularity](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/02-quarterly-granularity.md) | Python Expert | - | ⬜ Not started |
| 03 | [Linguist language aliases](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/03-linguist-aliases.md) | Python Expert | 01.0/02 | ✅ Complete |
| 04 | [Provider metadata, variants & registry entry](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/04-metadata-variants-and-registry.md) | Python Expert | 02, 03 | ⬜ Not started |
| 05 | [Innovation Graph fetch & parse](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/05-innovation-graph-fetch-and-parse.md) | Python Expert | 04, 01.0/04 | ⬜ Not started |
| 06 | [Innovation Graph normalize: global aggregation, share & rank](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/06-innovation-graph-normalize.md) | Python Expert | 05 | ⬜ Not started |
| 07 | [Octoverse annual rankings dataset](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/07-octoverse-annual-rankings.md) | Python Expert | 04 | ⬜ Not started |
| 08 | [Validate: named validation codes](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/08-validate.md) | Python Expert | 06, 07 | ⬜ Not started |
| 09 | [Fixtures, golden outputs & contract tests](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/09-fixtures-and-contract-tests.md) | Testing Expert | 08, 01.0/07 | ⬜ Not started |
| 10 | [Provider documentation](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/10-docs.md) | Docs Writer | 09 | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Add a `github` provider carrying two **independent** variants selected with
`--source octoverse|innovation-graph`: the Octoverse annual top-languages ranking (published
ranks) and the GitHub Innovation Graph quarterly per-economy developer counts (aggregated
to a global series, explicitly flagged as derived). Neither variant is interchangeable with
RedMonk's GitHub-derived component.

## Baseline (what already exists)

- `models.py:Granularity` has only `YEAR` and `MONTH`; Innovation Graph is quarterly.
  `observations.granularity` is a `TEXT` column, so adding a value needs **no migration**,
  but `Granularity` is part of the natural key.
- `providers/redmonk.py` - RedMonk ranks (GitHub+SO composite); this provider must say in
  its caveats that it is a different measure.
- Shared helpers from Task 01.0: `LanguageNormalizer.try_resolve(..., rating_id=)`
  ([01.0/02](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/02-rating-scoped-aliases.md)),
  `load_cached_payload` / `HttpClientFactory.get_json`
  ([01.0/04](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/04-fetch-api-and-offline-cache.md)),
  `tests/contract/_golden.py`
  ([01.0/07](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/07-fixtures-and-contract-tests.md)).
  If this task starts first it lands those pieces itself, per the same specs.
- Bare `"rank"` comparisons: fixed in
  [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata), not here.

## Design notes

- **Metric IDs:** `github-octoverse-rank` (annual, raw, published rank),
  `github-innovation-graph-pushers` (quarterly, derived global sum),
  `github-innovation-graph-share` (quarterly, derived), `github-innovation-graph-rank`
  (quarterly, derived). Variant is part of the metric ID so a query can never silently mix
  them.
- **Innovation Graph source (verified):** `github/innovationgraph` repo,
  `data/languages.csv` - columns `num_pushers, language, iso2_code, year, quarter`;
  quarterly from 2020-Q1; **CC0-1.0**; updated quarterly, previous versions in git history.
  An economy/language cell is only published with **≥100 developers**, so a global sum is an
  **undercount** biased against small languages → `derivation_method=
  "sum_over_economies:suppressed_below_100"`, caveat in metadata. Fetch pinned to a commit
  SHA (`raw.githubusercontent.com/github/innovationgraph/{sha}/data/languages.csv`), SHA
  stored in `source_document_id`, for reproducibility.
- **Octoverse source (verified):** annual blog post; there is no machine-readable dataset.
  The ranking basis changed over the years (e.g. 2025: TypeScript #1 by **monthly
  contributors**, published 2025-10-28; earlier editions ranked by contributors to
  repositories). Acquisition = curated bundled CSV `providers/data/github_octoverse.csv`
  (same pattern as the bootstrap providers) with one `MethodologyNote` per ranking basis.
  Only ranks that appear in the text/table are captured; **no chart pixel extraction**
  (`--allow-chart-extraction` is not implemented; see subtask 07).
- `--source auto` → `innovation-graph` (machine-readable preferred, per plan.md); `fetch all`
  therefore fetches Innovation Graph only; Octoverse needs `--source octoverse`.

### Open questions

- Per-economy series (e.g. `--economy US`)? Proposed default: out of scope; only the global
  aggregate is stored (`population="global (economies ≥100 developers)"`).
- Which Linguist "languages" to exclude (`Dockerfile`, `Makefile`, `HTML`, `CSS`, `Jupyter
  Notebook`)? Proposed default: map only languages in the canonical catalog; the rest go
  to `unmapped_language` warnings, but **are** included in the share denominator (total
  pushers across all published languages), recorded in metadata.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Both variants independently selectable via `--source`; each writes only its own metric IDs.
- [ ] No chart-derived value reaches the DB; every aggregated value has `is_derived=True`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- Innovation Graph repo & data: <https://github.com/github/innovationgraph>,
  <https://github.com/github/innovationgraph/tree/main/data>,
  datasheet: <https://github.com/github/innovationgraph/blob/main/docs/datasheet.md>.
- Innovation Graph programming-languages view: <https://innovationgraph.github.com/global-metrics/programming-languages>.
- Octoverse 2025: <https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/>.
- Cross-source survey: [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md) (in progress).
