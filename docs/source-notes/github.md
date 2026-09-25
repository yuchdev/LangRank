# GitHub

GitHub exposes two **independent** language-ranking signals selected with `--source`. They are not
interchangeable and never share a metric ID or axis, and neither equals RedMonk's GitHub-derived
component (RedMonk plots a GitHub-pull-request-rank vs Stack Overflow-tag-rank composite; see
[docs/source-notes/redmonk.md](/docs/source-notes/redmonk.md)). Both are distinct measures from
either GitHub variant here.

## Innovation Graph

- What it measures: quarterly count of unique developers making at least one git push to a repo
  containing a given Linguist-detected programming language, aggregated per economy (ISO-3166
  `iso2_code`); this provider derives a **global** series by summing published per-economy cells, an
  explicit `is_derived=True` value (`derivation_method="sum_over_economies:suppressed_below_100"`).
- Official source: `github/innovationgraph` repository, `data/languages.csv`
  (https://github.com/github/innovationgraph/blob/main/data/languages.csv); datasheet at
  https://github.com/github/innovationgraph/blob/main/docs/datasheet.md.
- Data shape (verified): columns `num_pushers, language, language_type, iso2_code, year, quarter`;
  the parser requires and reads `num_pushers, language, iso2_code, year, quarter` (a missing required
  column is a `ParseError`).
- Historical availability: 2020-Q1 onward; default fetch target is the last 10 years to the last
  published quarter.
- Acquisition mechanism: `api`/scheduled - one raw file per quarter fetched at a pinned commit SHA
  (`https://raw.githubusercontent.com/github/innovationgraph/{sha}/data/languages.csv`); the SHA is
  resolved from the commits API
  (`https://api.github.com/repos/github/innovationgraph/commits?path=data/languages.csv&per_page=1`)
  and stored in `source_document_id` for reproducibility. Previous quarterly files are deleted
  upstream but their contents are carried into the new file, so a pinned SHA is the only reproducible
  anchor.
- Imported metrics: `github-innovation-graph-pushers`, `github-innovation-graph-share`,
  `github-innovation-graph-rank` (all quarterly; `share`/`rank` are derived).
- Granularity: quarterly (`Granularity.QUARTER`).
- Language normalization rules: map each Linguist language name to the canonical language via the
  rating-scoped alias map; preserve the source string in the `SourceRecord`; unmapped Linguist
  entries (e.g. `Dockerfile`, `Makefile`, `HTML`, `CSS`, `Jupyter Notebook`) become
  `unmapped_language` warnings but are still counted in the share denominator (total pushers across
  all published languages), recorded in metadata.
- Known limitations: economy/language cells with fewer than **100 unique developers** are suppressed
  upstream, so the global sum is a systematic **undercount** biased against smaller languages;
  geolocation is IP-based; "pushers" measures push activity, not usage, code volume, or contributor
  headcount.
- Fallbacks: none - suppressed and missing cells stay missing; no interpolation, no synthetic global
  total beyond the explicit suppressed-below-100 sum.
- Terms/automation considerations: GitHub REST commits API is rate-limited to **60 requests/hour**
  unauthenticated and **5000 requests/hour** with a token (optional `GITHUB_TOKEN`); the raw file
  host (`raw.githubusercontent.com`) has its own throttling. This provider issues at most **2
  requests per fetch** (1 commits API + 1 raw download), so an unauthenticated schedule stays far
  under budget and `GITHUB_TOKEN` is optional headroom only, never required.
- Redistribution: licence **CC0-1.0** (public-domain dedication, verified via the datasheet) - the
  raw CSV may be cached and redistributed; the provider still records source URL and pinned SHA in
  provenance.
- Gate verdict: `approved-for-scheduled-fetch` - reviewer: Security Auditor agent - date:
  2026-09-25. Conditions: fetch pinned to a validated 40-hex commit SHA; `GITHUB_TOKEN` (if set)
  sent only to `api.github.com` and never persisted/logged; raw download host-pinned to
  `raw.githubusercontent.com` with a size cap; request budget ≤2 per fetch; global aggregate only,
  flagged `is_derived`. See [threat model](/docs/security/2026-09-25-github-fetch.md).
- Request budget: **2 requests per fetch** for `innovation-graph` (1 commits-API call to resolve the
  SHA + 1 raw CSV download); the provider must refuse to start if a planned run would exceed the
  applicable hourly ceiling (60 unauthenticated / 5000 with `GITHUB_TOKEN`).
- Parser/version notes: `github-innovation-graph-v1`.
- Last verified date: 2026-09-25.

## Octoverse

- What it measures: GitHub's **annual published** top-languages ranking; the ranking basis changes
  between editions and must be recorded per edition (e.g. the 2025 edition ranks by distinct
  **monthly contributors** - TypeScript #1 - whereas earlier editions ranked by contributors to
  repositories). Published ranks only; never a cross-source popularity score.
- Official source: annual github.blog Octoverse posts / octoverse.github.com; 2025 edition:
  https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/.
- Data shape: no machine-readable dataset exists - ranks are transcribed by hand from the published
  text/tables into a curated bundled CSV `src/langrank/providers/data/github_octoverse.csv`
  (`year,rank,language,ranking_basis,source_url,published_at`).
- Historical availability: per-edition; the note records, for every edition subtask 07 imports, which
  years expose a top-N list and under which ranking basis. Curated in
  `src/langrank/providers/data/github_octoverse.csv` (verified 2026-09-25):
  - **2024** (basis `contributors`, published 2024-10-29) - ranks 1-10. #1 Python is in the post
    prose; ranks 2-10 come from the explicitly numbered labels (`Python (1)` … `Go (10)`) in the
    ranking chart's published **alt text**. Ruled 2026-09-25: GitHub-authored numbered text counts
    as published text - it is not chart-geometry/pixel extraction, which stays forbidden.
  - **2025** (basis `monthly_contributors`, published 2025-10-28) - ranks 1-3 only (numbered in
    prose and alt text). Ranks 4+ appear only as an unordered "other top languages include …" list
    and are **omitted**, not guessed.
  - **2023, 2022, 2021 and earlier - omitted**: prose states at most #1-#2 (2023 skips #2), the
    rest is chart-only or JS-rendered without numbered text. Adding them would need chart
    extraction, which is out of scope.
- Acquisition mechanism: **manual curation only** - no network fetch; values transcribed only from
  text/tables GitHub actually printed. No chart-pixel extraction (`--allow-chart-extraction` is not
  implemented; a `octoverse-chart` source request is a `ProviderError`).
- Imported metrics: `github-octoverse-rank` (annual, raw published rank, `is_derived=False`).
- Granularity: annual (`Granularity.YEAR`).
- Language normalization rules: map each printed language name to the canonical language via the
  alias map; preserve the source string; no gaps filled and no ranks inferred.
- Known limitations: the ranking basis is not constant across editions, so ranks are not directly
  comparable year-over-year without reading each edition's `ranking_basis`; one `MethodologyNote` per
  distinct basis carries `valid_from`/`valid_to` edition years.
- Fallbacks: none - only ranks that appear in the published text/table are captured.
- Terms/automation considerations: GitHub content terms govern the blog/report; only the ranks
  (bare facts) and the source URL are stored, never report prose, images, or chart pixels. No
  automated fetch or scraping.
- Redistribution: store ranks (facts) plus the edition URL only; every CSV row carries a `source_url`
  to the edition post.
- Gate verdict: `manual-only` - reviewer: Security Auditor agent - date: 2026-09-25. Conditions: no
  network acquisition; ranks transcribed from published text/tables only; chart extraction refused.
- Request budget: **0 network requests** (bundled CSV read at `fetch()` time, same pattern as the
  bootstrap providers).
- Parser/version notes: `github-octoverse-v1`.
- Last verified date: 2026-09-25.
</content>
</invoke>
