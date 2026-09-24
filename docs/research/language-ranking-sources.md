# Programming-Language Ranking Sources: Landscape and LangRank Fit

**Last verified: 2026-09-24**

## 1. Purpose and methodological warning

This document surveys public and semi-public data sources that publish programming-language
popularity or activity signals. It records how each source is acquired, how far back it goes,
what its license allows, and how well it fits LangRank's provider pipeline and provenance rules
(see [CLAUDE.md](/CLAUDE.md) and [README.md](/README.md)). It feeds the provider roadmap
([Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) and later milestones) and a
future "source watch" automation (section 6).

**Methodological warning (restated from [README.md](/README.md)):** these sources measure different
things: search visibility, tutorial-search interest, code-hosting activity, Q&A activity,
self-reported usage, job demand, or a composite of several. Their values do not share an axis and
must never be merged or silently compared as one "popularity score." Every source below is tagged
with what it measures. Any cross-source comparison has to go through explicit, flagged
normalization (see [Milestone 0002](/docs/roadmap/0002-cross-rating-analysis/plan.md)).

Conventions in this document:

- "Verified" means checked against the live source on 2026-09-24, by fetching the page or API or
  downloading the file. Claims not checked that way are marked **(unverified)**.
- Proposed provider IDs are kebab-case and follow the style of the existing
  `stackoverflow-survey`.
- The Granularity enum in `src/langrank/models.py` currently has only `YEAR` and `MONTH`.
  Sources that need other granularities are flagged.

---

## 2. Summary table

| ID (proposed) | Measures | Access | History | Granularity | License / terms | Status in LangRank | Priority |
|---|---|---|---|---|---|---|---|
| `tiobe` | Search-engine visibility | HTML table (current month); full history sold as CSV | 2001-06 onward (paid); free: current top 50 + long-term snapshots | Monthly | Free display with attribution; history costs USD 5,000 | existing | P1 (maintain) |
| `pypl` | Tutorial-search interest (Google Trends) | JS data file on GitHub Pages (`PYPL/All.js`) | 2004-06 onward | Monthly (6-month smoothed) | CC BY 3.0 | existing | P1 (maintain) |
| `redmonk` | GitHub PRs + SO tags (composite rank) | HTML post + scatter-plot image | 2012 onward | Irregular, now about annual | No data license; blog copyright | existing | P1 (maintain) |
| `stackoverflow-survey` | Self-reported usage (+ admired/desired) | Official JSON + CSV archive on GitHub | 2011 onward (languages question from about 2013) | Annual | ODbL 1.0 / DbCL 1.0 | existing | P1 (upgrade source) |
| `stackoverflow-tags` | Q&A activity (questions per tag) | Stack Exchange API; SEDE; quarterly data dumps | 2008-08 onward | Monthly (derivable) | Content CC BY-SA 4.0; dump download terms bar LLM training; API terms | planned (0001 task 01.0) | P1 |
| `github-innovation-graph` | Code activity (unique pushers per language per economy) | CSV in `github/innovationgraph` | 2020-Q1 onward | **Quarterly**, per economy | CC0-1.0 | planned (0001 task 02.0) | P1 |
| `github-octoverse` | Code activity (contributors per language; annual top-10) | HTML report + charts | about 2014 onward (unverified for the earliest years) | Annual | GitHub site terms; no data license | planned (0001 task 02.0) | P2 |
| `ieee-spectrum` | Composite (search, SO, jobs, papers, GitHub, books, Discord) | Interactive (Flourish embed with JSON data); methodology article | 2013 onward (unverified for the earliest years) | Annual | IEEE copyright; no data license | planned (0001 task 03.0) | P1 |
| `jetbrains` | Self-reported usage (survey) | Raw-data ZIP (anonymized microdata) + report pages | 2017 onward (report); raw ZIP verified for 2024 and 2025 | Annual | 2024 report: CC BY-NC-SA 4.0 (non-commercial) | planned (0001 task 04.0) | P1 |
| `wikipedia-pageviews` | Encyclopedic interest (article views) | Wikimedia Analytics REST API | 2015-07 onward | Daily / monthly | Open data (license unverified; believed CC0) | candidate | P2 |
| `hn-hiring` | Job demand (share of HN "Who is hiring" posts mentioning a language) | HN APIs (Algolia/Firebase) → LangRank-derived counts; third-party sites | 2011-04 onward | Monthly | HN API terms (unverified); values would be LangRank-derived | candidate | P2 |
| `kaggle-survey` | Self-reported usage (DS/ML population) | CSV on Kaggle | 2017–2022 (ended) | Annual | Kaggle dataset terms (unverified) | candidate (static backfill) | P3 |
| `github-linguist-search` | Code hosting (repo counts per Linguist language) | GitHub Search API `language:` counts | None (current snapshot only) | Snapshot | GitHub API ToS | candidate | P3 |
| `package-registries` | Ecosystem downloads (not languages) | PyPI BigQuery, npm downloads API, crates.io dumps | Varies | Daily / monthly | Varies | candidate (separate "ecosystem" family) | P3 |
| `slashdata-communities` | Estimated developer-community size (survey + model) | Gated PDF / interactive | about 2017 onward (unverified) | About annual (biannual survey) | Proprietary | candidate (manual only) | P3 |
| `githut` | Code activity (GH Archive events by repo language) | JSON in `madnight/githut` | 2012–2024-Q1 (stale) | Quarterly | Code AGPL-3.0; data derived from GH Archive | rejected (stale) | reject |
| `languish` | Composite (GitHub + SO) | JSON in `tjpalmer/languish` | 2012–2025-Q2 | Quarterly | No license asserted | rejected | reject |
| `gh-archive` | Raw GitHub event stream | Hourly JSON.gz; BigQuery `githubarchive` | 2011-02 onward | Hourly | Open (terms unverified) | rejected (language field gone) | reject |
| `ossinsight` | Repo rankings within collections | Public API (beta) | 2011 onward | Varies | Terms unverified | rejected | reject |
| `google-trends` | Search interest | Official API in closed alpha; web UI only otherwise | 5-year rolling window (API) | Daily–yearly | Google ToS; no scraping | rejected (for now) | reject |
| `devjobsscanner`, `indeed` | Job demand | Blog posts (DevJobsScanner); occupation-level CSV (Indeed) | Short | Annual / daily | Proprietary / CC BY 4.0 (Indeed, not per language) | rejected | reject |
| `hackerrank`, `coderpad-codingame`, `leetcode` | Assessment / platform usage | Gated PDF reports / none | Short | Annual | Proprietary | rejected | reject |
| `reddit-subscribers` | Community size | Reddit API (paid tiers) | Third-party only | n/a | Reddit API terms; public counts removed 2025 | rejected | reject |
| `rosetta-code` | Chrestomathy task coverage | MediaWiki API | Snapshot only | Snapshot | GFDL (unverified) | rejected | reject |
| `langpop-2026` | Composite aggregator of other indices | Web site (bot-protected) | 2026 onward (unverified) | Weekly (claimed) | Unverified | rejected (circular) | reject |
| `openrouter`, `anthropic-economic-index` | AI-model / task usage | Web / Hugging Face | 2024–2025 onward | Weekly / periodic | Varies | rejected (not per language) | reject |
| `stackoverflow-trends` | Q&A tag share (chart tool) | Retired | — | — | — | defunct | — |
| `langpop-original`, `tlpi`, `trendyskills` | Composite / jobs | — | about 2008–2016 | — | — | defunct | — |

---

## 3. Scoring rubric and scores

Each criterion is scored 0–3. Higher is always better for LangRank.

| Criterion | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **D** Measurement distinctness (adds a signal not already covered) | Duplicates an existing source, or is derived from other indices | Mostly overlaps | Partially distinct | Unique signal family |
| **H** History depth (free, machine-obtainable) | None / snapshot only | < 5 years | 5–10 years | > 10 years |
| **M** Machine-readability | Chart images / gated PDF | HTML scraping of prose/tables | Semi-structured (embedded JSON, large microdata needing aggregation) | Official CSV/JSON/API |
| **L** License clarity (for ingest + raw-artifact caching) | Unknown / proprietary | Copyright-only, attribution-only, or ambiguous | Clear but restrictive (NC, no-LLM, API ToS) | Open license (CC0, CC BY, ODbL) |
| **S** Methodology stability | Broken / defunct | Frequent undocumented breaks | Documented breaks | Stable |
| **C** Maintenance cost (3 = cheapest) | Needs heavy infra (BigQuery $) or manual transcription | Per-edition manual work | Occasional parser updates | Set-and-forget |

| ID | D | H | M | L | S | C | Total /18 | Priority |
|---|---|---|---|---|---|---|---|---|
| `pypl` | 2 | 3 | 3 | 3 | 2 | 3 | **16** | P1 (existing) |
| `stackoverflow-survey` | 3 | 3 | 3 | 3 | 2 | 2 | **16** | P1 (existing) |
| `github-innovation-graph` | 3 | 1 | 3 | 3 | 2 | 3 | **15** | P1 |
| `wikipedia-pageviews` | 2 | 3 | 3 | 2 | 3 | 2 | **15** | P2 |
| `hn-hiring` | 3 | 3 | 3 | 2 | 2 | 1 | **14** | P2 |
| `stackoverflow-tags` | 2 | 3 | 3 | 2 | 1 | 2 | **13** | P1 |
| `tiobe` | 2 | 2 | 1 | 2 | 2 | 2 | **11** | P1 (existing) |
| `jetbrains` | 2 | 2 | 2 | 2 | 2 | 1 | **11** | P1 |
| `redmonk` | 1 | 3 | 1 | 1 | 1 | 2 | **9** | P1 (existing) |
| `ieee-spectrum` | 2 | 2 | 2 | 1 | 1 | 1 | **9** | P1 |
| `kaggle-survey` | 2 | 1 | 3 | 1 | 0 | 3 | **10** | P3 |
| `github-linguist-search` | 2 | 0 | 3 | 2 | 2 | 2 | **11** | P3 |
| `package-registries` | 1 | 2 | 2 | 2 | 2 | 1 | **10** | P3 |
| `github-octoverse` | 1 | 2 | 1 | 1 | 1 | 1 | **7** | P2 |
| `githut` | 1 | 2 | 3 | 1 | 0 | 2 | **9** | reject |
| `languish` | 0 | 2 | 3 | 0 | 1 | 2 | **8** | reject |
| `gh-archive` | 2 | 3 | 2 | 2 | 0 | 0 | **9** | reject |
| `ossinsight` | 1 | 2 | 2 | 1 | 1 | 1 | **8** | reject |
| `slashdata-communities` | 2 | 1 | 0 | 0 | 2 | 0 | **5** | P3 (manual) |
| `google-trends` | 1 | 1 | 1 | 1 | 1 | 1 | **6** | reject |
| `devjobsscanner` | 3 | 1 | 0 | 0 | 1 | 0 | **5** | reject |
| `hackerrank` / `coderpad-codingame` | 1 | 1 | 0 | 0 | 1 | 0 | **3** | reject |
| `reddit-subscribers` | 1 | 0 | 1 | 0 | 0 | 0 | **2** | reject |
| `rosetta-code` | 1 | 0 | 2 | 1 | 2 | 2 | **8** | reject |
| `langpop-2026` | 0 | 0 | 0 | 0 | 1 | 1 | **2** | reject |

Notes on scoring:

- The planned `github-octoverse` scores low on its own. Its value is as annual editorial context
  next to `github-innovation-graph`, and for years before 2020 that Innovation Graph does not cover.
- `redmonk` and `ieee-spectrum` score low mostly because of machine-readability and license. Both
  are still worth having as widely cited, distinct editorial composites.
- A totals tie is broken by D, the distinctness score.

---

## 4. Per-source details

### TIOBE Index (`tiobe`, existing)

- **Measures:** search-engine visibility. The query is `+"<language> programming"`, run on 25
  engines chosen from Similarweb's top sites. Each engine's hits are normalized to its total, then
  averaged; a confidence factor removes false positives. Explicitly "not about the best
  programming language or the language in which most lines of code have been written."
  (https://www.tiobe.com/tiobe-index/programminglanguages_definition/)
- **Publisher:** TIOBE Software BV. **URL:** https://www.tiobe.com/tiobe-index/
- **Acquisition:** HTML tables for the current month (top 20 with ratings, plus positions 21–50),
  and a "very long term history" table sampled every 5 years. The full monthly history for 150+
  languages from June 2001 costs **USD 5,000** as CSV (sales@tiobe.com), verified on the index page.
- **Machine-readability:** HTML only for free data. Historical monthly values have to come from
  the paid dataset, archived snapshots (Wayback), or third-party reconstructions. The existing
  provider already flags the last as `third_party_reconstruction`.
- **History / granularity:** monthly, 2001 onward (paid). The latest edition verified is September
  2026, with Python 17.76%, C 10.28%, C++ 8.67%, Java 7.54%, C# 4.22%.
- **Cadence:** monthly, usually in the first days of the month.
- **Metrics / units:** rank (integer), rating (% share of normalized hits), month-over-month
  change.
- **Terms:** display is allowed with attribution to www.tiobe.com. Redistributing the paid
  history is presumably not allowed **(unverified)**.
- **Methodology breaks:** the engine set and confidence factors change without a public changelog.
  The definition page carries no dated history of changes **(unverified whether one exists
  elsewhere)**. Classic known discontinuities, such as Google hit-count changes around 2004,
  remain **unverified**.
- **Language quirks:** grouped names (Visual Basic covers VB/VB6/VB.NET; Assembly language; C#
  variants). "Visual Basic" versus "Visual Basic .NET" was split in some past years
  **(unverified)**. C and C++ are separate.
- **Stability risk:** medium. The free surface is stable, but the free history is not.
- **Fit:** existing. Keep. Store each monthly HTML snapshot as a `RawArtifact` so LangRank builds
  its own history going forward.

### PYPL (`pypl`, existing)

- **Measures:** Google Trends search share of "<language> tutorial" queries, normalized each
  month and smoothed over 6 months (https://pypl.github.io/PYPL.html).
- **Publisher:** Pierre Carbonnelle (PYPL). **Repo:** https://github.com/pypl/pypl.github.io
- **Acquisition:** `PYPL/All.js`, a Google Charts `graphData` array with one row per month and
  one column per language (verified). Per-country files `DE.js`, `FR.js`, `GB.js`, `IN.js`, and
  others exist. Raw URL:
  https://raw.githubusercontent.com/pypl/pypl.github.io/master/PYPL/All.js
- **History / granularity:** monthly from `new Date(2004,5,1)` (JS months are 0-based, so June 2004)
  to September 2026. That is 286 rows, verified.
- **Cadence:** monthly. The September 2026 commit ("Sep 26") landed on 2026-09-10.
- **Metrics:** share (a fraction, 0–1, of tutorial searches), plus derived rank.
- **License:** CC BY 3.0 Unported (stated on the page).
- **Methodology breaks and gotchas:** the whole history is recomputed each month from a fresh
  Google Trends export. Past values can shift slightly between fetches, so `raw_record_hash` will
  legitimately change for old periods. That is a re-statement, not corruption, and should be
  logged as one. The language set changes over time: 30 columns now, including `Zig`.
- **Language quirks:** combined `C/C++` (keep as canonical `c-cpp`, as the existing notes say);
  `Delphi/Pascal`; `Visual Basic` separate from `VBA`.
- **Stability risk:** low to medium (single maintainer).
- **Fit:** existing. The current provider is CSV-backed; switching to `All.js` gives an official
  machine-readable fetch.

### RedMonk Programming Language Rankings (`redmonk`, existing)

- **Measures:** a composite rank that correlates GitHub pull-request counts (from GH Archive,
  excluding forks, language taken from the base repository) with Stack Overflow tag counts (from
  SEDE). The output is a scatter plot and a top-20 rank list with ties
  (https://redmonk.com/sogrady/2026/04/14/language-rankings-1-26/).
- **Publisher:** RedMonk (Stephen O'Grady). **Archive:**
  https://redmonk.com/sogrady/category/programming-languages/
- **Acquisition:** HTML blog post (top-20 list) plus a plot image. A companion "Top 20 over time"
  post by Rachel Stephens exists (https://redmonk.com/rstephens/2026/04/14/top20-jan2026/).
- **History / cadence (verified from the archive):** February 2012, September 2012, then January
  and June each year from 2013 to 2022. After that: **January 2023 (no June 2023), January 2024,
  June 2024, January 2025 (published 2025-06-18; no June 2025), January 2026 (published
  2026-04-14).** The cadence is now effectively annual, and the edition label (the data quarter)
  differs from the publication date by several months.
- **Metrics:** ordinal rank with ties, for the top 20 only. Positions below 20 appear only in the
  plot.
- **Terms:** no data license; blog content under RedMonk copyright **(unverified exact terms)**.
- **Methodology breaks (verified in the January 2026 post):** Stack Overflow's relevance has
  declined, making its tags "less representative," and H2-2025 GitHub PR volumes were
  "anomalously low." LangRank's own check points to a likely cause: since GitHub's
  **2025-10-07** Events API change, `PullRequestEvent` payloads in GH Archive carry only
  `url, id, number, head, base`, and `base.repo` holds only `id, url, name`. **The
  `base.repo.language` field is gone** (verified by comparing GH Archive hours 2025-03-03-12 and
  2026-03-02-12). Treat RedMonk's GitHub axis after October 2025 as methodologically suspect.
- **Language quirks:** CSS and Shell are ranked alongside programming languages; ties are common.
- **Stability risk:** high (cadence drift, degraded inputs).
- **Fit:** existing. Store `source_published_at` separately from the edition label. Never
  interpolate between editions.

### Stack Overflow Developer Survey (`stackoverflow-survey`, existing)

- **Measures:** self-reported usage. The language question asks which "programming, scripting,
  and markup languages" the respondent "has done extensive development work in over the past
  year," plus which they want to work in (desired and admired).
- **Publisher:** Stack Overflow / Stack Exchange Inc. **URLs:** https://survey.stackoverflow.co/,
  https://github.com/StackExchange/Survey
- **Acquisition (new, verified):** the official archive
  https://github.com/StackExchange/Survey/tree/main/packages/archive/{YEAR} has `results.csv`
  (raw microdata via Git LFS, about 141 MB for 2025; the media URL is
  `https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/2025/results.csv`),
  `schema.csv`, `survey.pdf`, and, **for 2017–2025, aggregated `json/*.json` result files**
  (added 2026-08-24). For 2025, `json/technology.json` contains `Language`, with datasets for All
  Respondents (`total_respondents` 31,771), Professional Developers (24,759), Learning to Code,
  and AI-user subgroups. It also has `WW_Language` (worked-with to want-to-work-with, sankey) and
  `DA_Language` ("Desired and Admired", dumbbell). These give official aggregates with explicit
  denominators, with no need to re-tabulate microdata. The older ZIP host
  (`info.stackoverflowsolutions.com/.../stack-overflow-developer-survey-{YEAR}.zip`) still serves
  2017 but redirects for 2023 and later.
- **History:** 2011–2025 editions. The archive README lists open, close, and release dates.
  Release dates were 2022-06-22, 2023-06-13, 2024-07-24, and 2025-07-29.
- **2026 edition:** opened **2026-06-23**
  (https://stackoverflow.blog/2026/06/23/the-2026-developer-survey-is-now-open-for-human-developers-only/),
  later than prior years. **Results are not published as of 2026-09-24**: survey.stackoverflow.co
  lists 2025 as the latest, and the archive has no 2026 directory.
- **License:** ODbL 1.0 for the database and DbCL 1.0 for contents. Attribution: "Stack Overflow
  Developer Survey, Stack Exchange Inc." Repo code is Apache-2.0.
- **Methodology breaks:** question wording and answer options change yearly. "Loved/Dreaded/Wanted"
  became "Admired/Desired" in 2023 **(unverified exact year, believed 2023)**. Survey timing moved
  from January–February (≤2020) to May–June (2021 onward). Respondent counts are falling (49k+
  total in 2025). Years are labelled by release year.
- **Language quirks:** HTML/CSS and SQL are included as "languages"; "Bash/Shell (all shells)";
  write-ins are listed separately.
- **Stability risk:** low to medium.
- **Fit:** existing. **Recommend switching the provider to the official JSON aggregates.** Add
  `admired_percent` and `desired_percent` as distinct metrics, and keep subgroup (all versus
  professional) as distinct metrics too.

### Stack Overflow tags / questions (`stackoverflow-tags`, planned 0001 task 01.0)

- **Measures:** Q&A activity: the number of new questions carrying a language tag per period.
- **Publisher:** Stack Exchange Inc.
- **Acquisition options (verified 2026-09-24):**
  1. **Stack Exchange API v2.3.**
     `https://api.stackexchange.com/2.3/questions?site=stackoverflow&tagged={tag}&fromdate={unix}&todate={unix}&filter=total`
     returns `{"total": N}` and works anonymously. Verified: `rust`, June 2025 = **87**. All
     questions for the same window via `/search/advanced ... filter=total` = **7,752**. Quota is
     about 300 requests/day anonymous and 10,000/day with a registered key **(unverified current
     numbers)**. Counts reflect the *current* state (deleted questions excluded, tags as
     re-tagged), so old months can drift between fetches.
  2. **Stack Exchange Data Explorer (SEDE)**, https://data.stackexchange.com/, is bot-protected
     (HTTP 403 to curl and WebFetch). RedMonk still uses it in 2026. It is refreshed weekly
     **(unverified)** and is interactive only, so it is unsuitable for unattended fetch.
  3. **Data dumps.** Since mid-2024 the official dumps are downloaded per site after login, and the
     downloader must agree not to use them for "training a large language model"
     (https://devclass.com/2024/07/30/stack-exchange-restricts-access-to-dump-of-user-contributed-data-as-critics-complain-license-permits-reuse-for-any-purpose/,
     https://search.feep.dev/blog/post/2025-02-20-state-of-stackexchange). Community mirrors on
     the Internet Archive continue quarterly: `stackexchange_20250930`, `_20251231`, `_20260331`,
     `_20260630` (the last posted 2026-08-17, verified via archive.org search). Content is
     CC BY-SA 4.0.
  4. **Stack Overflow Trends** (insights.stackoverflow.com/trends) is **retired**. It now
     redirects to trends.stackoverflow.co, which serves the 2017 launch blog post (verified).
- **History:** monthly, 2008-08 onward (derivable from the API or dumps).
- **Metrics:** `questions` (count), `question_share` (a fraction of a declared denominator),
  `rank`.
- **Methodology risks:** question volume has collapsed. devclass reports 3,862 questions in
  December 2025, down 78% year over year, against more than 200k per month at the 2014 peak
  (https://devclass.com/2026/01/05/dramatic-drop-in-stack-overflow-questions-as-devs-look-elsewhere-for-help/;
  the tool behind the figure is unspecified). Recent monthly counts per language are small (tens
  to hundreds), so shares are noisy. Tag synonyms and renames need a curated map.
- **Stability risk:** high (declining platform; access-policy churn).
- **Fit:** planned. Use the API with `filter=total`. Cache each response as a `RawArtifact` and
  record `retrieved_at`. Treat re-fetch drift as re-statement. Declare the denominator explicitly
  (see section 5).

### GitHub Innovation Graph (`github-innovation-graph`, planned 0001 task 02.0)

- **Measures:** code activity: *the number of unique developers in each economy who made at least
  one git push to a repository with a given language during each quarter* (datasheet:
  https://github.com/github/innovationgraph/blob/main/docs/datasheet.md). Language detection uses
  Linguist repository languages.
- **Publisher:** GitHub. **Repo:** https://github.com/github/innovationgraph.
  **Site:** https://innovationgraph.github.com/
- **Acquisition (verified):**
  `https://raw.githubusercontent.com/github/innovationgraph/main/data/languages.csv`, with
  columns `num_pushers,language,language_type,iso2_code,year,quarter`. The file has 180,339 rows,
  185 economies, and 404 language names. `language_type` is one of `programming` (144k rows),
  `markup` (35k), `data`, or `prose`. Releases are tagged (`v1.0.11`, 2026-07-07 = Q1 2026 data).
  Other files: `git_pushes`, `developers`, `organizations`, `repositories`, `licenses`, `topics`,
  `economy_collaborators`.
- **History / granularity:** **quarterly, per economy, 2020-Q1 to 2026-Q1.** There is **no global
  row**. Minimum `num_pushers` is 101, because a metric is reported only when at least 100 unique
  developers do it in that economy and quarter.
- **Cadence (verified from `languages.csv` commit history):** Q1-2025 data on 2025-08-13, Q2 on
  2025-11-04, Q3 on 2026-01-28, Q4 on 2026-05-07, Q1-2026 on 2026-07-07. The lag is about 3–4
  months.
- **License:** CC0-1.0 (data and code; verified via the GitHub API).
- **Methodology breaks:** the 2025-04-22 commit "add non-programming languages back in" means the
  set of `language_type` values published has changed at least once. Bots and inauthentic
  accounts are excluded. Private activity is excluded.
- **Language quirks:** Linguist names (`Jupyter Notebook` typed as markup, `Vim Script`,
  `Objective-C++`, `HCL`, `Dockerfile`, `Makefile`). HTML and CSS appear as markup.
- **Stability risk:** low to medium.
- **Fit:** the best new 0001 source. See section 5 for the aggregation and granularity issues.

### GitHub Octoverse (`github-octoverse`, planned 0001 task 02.0)

- **Measures:** code activity. In 2025 the ranking was by "the number of distinct monthly
  contributors who committed code in that language," measured on a September 1, 2024 – August 31,
  2025 window, with a top-10 snapshot for August 2025. TypeScript was #1 (about 2.64M monthly
  contributors, +66.6% YoY), ahead of Python (2.55M) and JavaScript (2.15M). Also published:
  "fastest-growing" languages by percentage (Luau, Typst, Astro, Blade, TypeScript)
  (https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/,
  published 2025-10-28, updated 2026-02-28).
- **Publisher:** GitHub. **URLs:** https://octoverse.github.com/ (current), archives such as
  https://octoverse.github.com/2016/, https://octoverse.github.com/2017/,
  https://octoverse.github.com/2022/top-programming-languages
- **Acquisition:** HTML report and chart images. No official per-language dataset; the report
  points readers to the Innovation Graph.
- **History:** annual, about 2014 onward. The earliest editions and their exact metric
  definitions are **unverified**. The metric definition has changed across editions (PRs,
  contributors to repos by primary language, monthly contributors) **(unverified per year)**, so
  editions are not a continuous series.
- **Cadence:** late October or early November (2025: October 28).
- **Terms:** GitHub site terms; no data license.
- **Stability risk:** medium (the definition changes).
- **Fit:** P2, and only as manually curated annual top-N ranks with a per-edition
  `metric_definition` note. Never derive values from chart pixels without the flag the plan
  already requires.

### IEEE Spectrum Top Programming Languages (`ieee-spectrum`, planned 0001 task 03.0)

- **Measures:** a composite. The 2025 methodology uses Google search hits for "X programming
  language," Stack Overflow tagged questions (past week), IEEE Xplore articles, IEEE Job Site
  postings, CareerBuilder (400 sampled U.S. ads), GitHub (top 50 languages, Q1 2025), Trinity
  College Dublin library books, and Discord tags via Disboard. Collection is now **manual**
  "due to the difficulty of keeping up with API changes and terminations." 64 languages are
  tracked (https://spectrum.ieee.org/top-programming-languages-methodology-2025). The weights per
  profile are not published.
- **Profiles:** **Spectrum** (default, weighted toward IEEE members), **Jobs**, **Trending**.
- **Acquisition (verified for 2025):** the article
  https://spectrum.ieee.org/top-programming-languages-2025 (published 2025-09-23) and the
  interactive https://spectrum.ieee.org/top-programming-languages embed a **Flourish
  visualisation 24825595**. Its embed page `https://flo.uri.sh/visualisation/24825595/embed`
  carries a `_Flourish_data` JSON array of `{filter: "Spectrum"|"Jobs"|"Trending", label,
  value, metadata}`. Row counts: Spectrum 52, Jobs 51, Trending 53. Scores are normalized so the
  top language = 1 (Python = 1 in all three; Spectrum #2 Java 0.499; Jobs #2 SQL 0.912).
- **History gotcha:** `/top-programming-languages-2024` now **redirects to the current (2025)
  interactive**. Past editions are not preserved at stable URLs, so historical values need
  Wayback snapshots (for example, 2024-08-22 captures of the 2024 page exist) or contemporary
  articles. The 2023 URL returns 404, and Wayback has no capture under that slug. Earlier-edition
  data formats are **unverified**.
- **History:** annual, about 2013 onward **(unverified start)**. Verified publication dates:
  2021-08-24, 2022-08-23, about 2024-08-22 (Wayback), 2025-09-23.
- **2026 edition:** not published as of 2026-09-24 (`/top-programming-languages-2026` returns
  404). IEEE ran an event framed as whether AI means "the end of distinct programming languages"
  and whether the ranking would continue **(discontinuation unverified)**.
- **Terms:** IEEE copyright; no data license.
- **Methodology breaks:** input sources change almost every year (for example, API-based to
  manual in 2025). Profile set: an "Open" profile existed in early years **(unverified)**.
- **Stability risk:** high.
- **Fit:** P1 as planned, but in practice a manual or semi-manual per-edition ingest. Keep one
  metric per profile, and store `score` as the normalized 0–1 value exactly as published.

### JetBrains State of Developer Ecosystem (`jetbrains`, planned 0001 task 04.0)

- **Measures:** self-reported usage from the JetBrains survey. Language questions cover languages
  used in the last 12 months, primary languages, and "Which of the following languages are you
  planning to adopt or migrate to?" (2024 report).
- **Publisher:** JetBrains Strategic Research. **URLs:** https://devecosystem-2025.jetbrains.com/,
  https://www.jetbrains.com/lp/devecosystem-2024/, methodology
  https://lp.jetbrains.com/developer-ecosystem-2025-methedology/ (sic).
- **Acquisition (verified):**
  - 2025: `https://resources.jetbrains.com/storage/products/research/DevEco2025/RawData.zip`
    (HTTP 200, 98.3 MB, Last-Modified 2025-10-16).
  - 2024: `https://resources.jetbrains.com/storage/products/research/DevEco2024/RawData.zip`
    (HTTP 200).
  - The same URL pattern returns 403 for 2017–2023 and 2026. The 2022 page says "raw data from our
    DevEco 2022 survey is now available," but at a different URL (unverified). Raw data for
    2018–2021 is **unverified**.
  - The raw data is respondent-level microdata (500+ or 600+ questions), so LangRank would have
    to tabulate percentages itself, applying JetBrains' weighting. Whether weights are shipped in
    the ZIP is **unverified**. The published report percentages are the official values.
- **Survey facts:** 2025 ran April–June 2025 with 24,534 respondents after cleaning, from 194
  countries. 2024 ran May–June 2024 with 23,262. Weighting is three-stage: regional
  professional-developer populations; students and unemployed fixed at 17% per country; and
  language, employment, and JetBrains-product balancing. JetBrains users are down-weighted 10%.
- **Cadence:** survey in spring or summer; report October–December (2024 report 2024-12-11; 2025
  report about October 2025). The **2026 survey** (tenth edition) ran May–July 2026 with 15k+
  professional developers. Only partial findings are out, such as AI coding agents
  (https://blog.jetbrains.com/research/2026/08/ai-coding-agent-adoption-2026/). The full report
  with language data has **not been verified as published**.
- **License:** 2024 report: "its contents may be used only for non-commercial purposes," under
  **CC BY-NC-SA 4.0**. The 2025 raw-data page states no specific license. The 2023 report asked
  for credit only **(unverified wording)**.
- **Methodology breaks:** from 2025 the population is professional-developer-weighted. The 2026
  sample is described as professional developers. Question wording and answer lists change
  **(exact per-year wording unverified; must be captured from each year's questionnaire)**.
- **Stability risk:** medium.
- **Fit:** P1 as planned. Start from report-published percentages for "used in last 12 months"
  and treat microdata re-tabulation as derived (`is_derived=True`). The NC license means the
  project should document whether cached raw artifacts may be redistributed.

### Wikipedia pageviews (`wikipedia-pageviews`, candidate)

- **Measures:** encyclopedic interest: human (non-spider) views of each language's Wikipedia
  article.
- **Publisher:** Wikimedia Foundation. **API:**
  `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{daily|monthly}/{start}/{end}`
  (verified: `en.wikipedia/all-access/user/Rust_(programming_language)/monthly` gives January
  2025 = 62,398). Docs:
  https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/examples/page-metrics.html,
  https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Traffic/Pageviews
- **History:** the API covers 2015-07 onward. Older pagecounts dumps exist but use a different
  methodology.
- **Terms:** a descriptive User-Agent is required. Data is openly licensed (**unverified**:
  believed CC0). Rate limits are **unverified**.
- **Gotchas:** article titles are ambiguous or get renamed (`Go_(programming_language)`,
  `C_Sharp_(programming_language)`), so a curated title map with redirect handling is needed.
  Each language edition of Wikipedia is a separate project; start with `en` only and store the
  project in the metric ID. Bot filtering changed around 2016 when the `automated` agent type
  appeared **(unverified date)**.
- **Fit:** P2. A distinct, stable, open, monthly signal.

### Hacker News "Who is hiring?" (`hn-hiring`, candidate)

- **Measures:** job demand among HN-posting employers: the share of top-level comments in the
  monthly "Ask HN: Who is hiring?" thread that mention a language.
- **Primary data:** HN Algolia API (https://hn.algolia.com/api) and Firebase API
  (https://github.com/HackerNews/API). Threads are posted monthly by `whoishiring` since 2011-04.
- **Third-party aggregators:** https://www.hntrends.com/ (Ryan Williams; last updated May 2024,
  so stale), https://hnhiring.com/ (live; per-technology monthly pages such as
  https://hnhiring.com/technologies/java; a trends page at https://hnhiring.com/trends; no export
  found), https://hackernewstrends.com/who-is-hiring, https://hacker-hirings.com/. None publishes
  a licensed dataset **(unverified)**.
- **Gotchas:** LangRank would compute the metric itself from primary posts, so every value is
  `is_derived=True` with a documented `derivation_method` (term dictionary + version). Language
  names clash with common words (`Go`, `C`, `R`, `Swift`, `Rust`) and need careful regexes and a
  versioned dictionary. The number of posts per thread varies strongly, so report both counts and
  shares.
- **Terms:** HN API usage terms **unverified**; content belongs to the posters.
- **Fit:** P2. The only open, long-history, monthly jobs-flavoured signal found.

### Kaggle ML & DS Survey (`kaggle-survey`, candidate, static)

- **Measures:** self-reported language use among data-science and ML practitioners.
- **URLs:** https://www.kaggle.com/c/kaggle-survey-2022 (and the 2017–2021 editions).
- **Status:** **ended after 2022.** No 2023 survey; users were still asking about it in March 2024
  (https://www.kaggle.com/discussions/product-feedback/483573). The 2022 edition had 23,997
  responses.
- **License:** Kaggle competition-data terms **(unverified)**.
- **Fit:** P3. A one-off static backfill (2017–2022) with a clearly different population.

### GitHub Linguist repo counts via the Search API (`github-linguist-search`, candidate)

- **Measures:** code hosting: the count of public repositories whose primary Linguist language is
  X (`GET /search/repositories?q=language:X`, `total_count`), optionally filtered by `pushed:` or
  `created:` date ranges.
- **History:** none from the source. `created:` ranges allow back-computing repos *created* per
  month, but only for repos that still exist, which is survivorship-biased.
- **Terms:** GitHub API ToS. The search rate limit is about 30 requests/minute authenticated
  **(unverified current value)**.
- **Fit:** P3. Only as a forward-collected snapshot series, with `retrieved_at` as the period.

### Package registries (`package-registries`, candidate, separate family)

- **Measures:** *ecosystem* activity (downloads, new packages), **not languages**. Downloads are
  inflated by CI and mirrors, and registries are not one-to-one with languages (npm serves both
  JavaScript and TypeScript).
- **Sources:** PyPI downloads (BigQuery `bigquery-public-data.pypi.file_downloads`, **unverified
  current name**); npm downloads API (`api.npmjs.org/downloads`, history limited to about 18
  months per query, **unverified**); crates.io daily DB dump (**unverified license**);
  Libraries.io (API with key, 60 requests/minute; owner Tidelift is being acquired by Sonar)
  (https://libraries.io/api).
- **Fit:** P3. If ever added, as a distinct `ecosystem-*` metric family that is never plotted as
  language popularity.

### SlashData Developer Nation, "Sizing programming language communities" (`slashdata-communities`, candidate)

- **Measures:** estimated active developers per language community, in millions. Built from the
  biannual Developer Nation survey plus SlashData's developer-population model.
- **URLs:** https://www.slashdata.co/free-industry-reports/sizing-programming-language-communities,
  https://www.developernation.net/resources/reports/sizing-programming-language-communities/
- **Latest:** the report is based on the **31st edition (Q1 2026)**, with 11,500+ respondents
  across 95 countries. The 30th edition was Q3 2025.
- **Access:** gated report (Research Space registration). Per-language numbers are not available
  as data.
- **License:** proprietary; no redistribution terms stated.
- **Fit:** P3. Manual transcription only, if at all.

### GitHut 2.0 (`githut`, rejected)

- **What:** quarterly GitHub event counts (PRs, pushes, stars, issues) by repository language from
  GH Archive via BigQuery. https://madnight.github.io/githut/,
  https://github.com/madnight/githut
- **Status:** **stale.** The last push was 2024-04-03 ("add 2024/Q1 datasets"). Code is
  AGPL-3.0. The project had already replaced the stale BigQuery
  `github_repos.languages` table (last updated November 2022) with PR-event language extraction.
  That source broke on 2025-10-07 (see RedMonk).
- **Reject reason:** stale, and its method cannot continue. At most a documented historical
  reference.

### Languish (`languish`, rejected)

- **What:** mean-score composite of GitHub (GH Archive) and Stack Overflow (SEDE) quarterly
  percentages. https://tjpalmer.github.io/languish/, https://github.com/tjpalmer/languish
- **Status:** data through 2025-Q2. The last push was 2026-04-06 ("Finally push old update
  attempts"). No license asserted (GitHub API `spdx_id: NOASSERTION`).
- **Reject reason:** no license, it duplicates RedMonk's inputs, and it depends on the broken
  PR-language field.

### GH Archive / BigQuery (`gh-archive`, rejected as a provider)

- **What:** the raw public GitHub event stream, hourly, 2011-02-12 onward.
  `https://data.gharchive.org/YYYY-MM-DD-HH.json.gz`; BigQuery dataset `githubarchive`
  (https://www.gharchive.org/).
- **Breaking change:** GitHub trimmed Events API payloads (brownout 2025-09-08, effective
  **2025-10-07**, https://github.blog/changelog/2025-08-08-upcoming-changes-to-github-events-api-payloads/).
  PR events no longer carry the repo language, and PushEvent lost its commit summaries (verified
  directly in GH Archive files).
- **Reject reason:** after October 2025 there is no language without joining every repo against
  the REST API. It also needs BigQuery billing, and Innovation Graph already publishes an official
  aggregate.

### OSS Insight (`ossinsight`, rejected)

- **What:** PingCAP's analytics over GitHub events. Public API (beta) at
  `https://api.ossinsight.io/v1/` (verified reachable). "Programming Language" is a *collection of
  repos* (compilers and runtimes), not a per-language usage metric
  (https://ossinsight.io/collections/programming-language).
- **Reject reason:** it ranks repositories, not languages, and inherits the GH Archive breakage
  **(unverified whether OSS Insight re-derives language)**.

### Google Trends (`google-trends`, rejected for now)

- **What:** search interest. An official **Google Trends API (alpha)** was announced 2025-07-24
  (https://developers.google.com/search/blog/2025/07/trends-api). Access is application-only. It
  offers a rolling **5-year** window, daily to yearly aggregation, and "consistently scaled"
  values (https://developers.google.com/search/apis/trends; still alpha as of 2026-09-24).
- **Reject reason:** PYPL already covers a Google-Trends-derived signal. Scraping the web UI
  violates the ToS, and the alpha is gated with only 5 years of history. Re-evaluate if the API
  reaches general availability.

### Job-posting indices (`devjobsscanner`, `indeed`, rejected)

- **DevJobsScanner:** annual blog posts on "most demanded languages," for example about 3M
  developer jobs analysed in 2025
  (https://www.devjobsscanner.com/blog/top-8-most-demanded-programming-languages/). The site
  returns 403 to automated fetch, publishes no dataset, and is proprietary.
- **Indeed Hiring Lab:** CC BY 4.0 daily job-postings index on GitHub
  (https://github.com/hiring-lab/job_postings_tracker), with a "Software Development" series from
  2020-02-01 (FRED `IHLIDXUSTPSOFTDEVE`). It is **occupation-level, not per language**.
- **Reject reason:** no open per-language series. Indeed could at most serve as context for a job
  denominator.

### HackerRank, CoderPad/CodinGame, LeetCode (rejected)

- HackerRank Developer Skills Report (annual; 2025 edition at
  https://www.hackerrank.com/reports/developer-skills-report-2025) and the CoderPad + CodinGame
  "State of Tech Hiring" (annual, about 3,000 respondents,
  https://coderpad.io/survey-reports/coderpad-and-codingame-state-of-tech-hiring-2025/) are gated
  marketing PDFs with inconsistent metrics. LeetCode publishes no language report.
- **Reject reason:** proprietary, not machine-readable, short and inconsistent series.

### Reddit subreddit subscribers (`reddit-subscribers`, rejected)

- In September 2025 Reddit replaced public member counts with "weekly visitors" and
  "contributions" (rolling 28-day averages). Subscriber counts are now visible to moderators only
  (https://support.reddithelp.com/hc/en-us/articles/41043361207316-Understanding-weekly-visitors-and-contributions-on-Reddit).
  The API has been commercial-tiered since 2023.
- **Reject reason:** the metric no longer exists publicly, history exists only in third-party
  scrapes, and the ToS is restrictive.

### Rosetta Code (`rosetta-code`, rejected)

- "Rank languages by popularity" counts tasks solved per language (about 1,000+ languages).
  Hosted on Miraheze since August 2022 (https://rosettacode.org/wiki/Rosetta_Code). MediaWiki API
  available. Content license GFDL **(unverified)**.
- **Reject reason:** measures chrestomathy contributions, not usage, and has no time series.

### LangPop.com, 2025–2026 incarnation (`langpop-2026`, rejected)

- A new site at https://langpop.com/ describes itself as a "transparent" composite of 7 sources
  (GitHub, jobs, Stack Overflow, Google Trends, package managers, Reddit, tutorials) updated
  weekly **(unverified; the site is behind a Vercel bot checkpoint, and claims are taken from
  search-result snippets)**. It is unrelated to the defunct original LangPop.
- **Reject reason:** an aggregate of other indices, which is circular for LangRank. Ownership and
  license are unclear.

### AI-usage-based signals (`openrouter`, `anthropic-economic-index`, rejected)

- OpenRouter rankings (https://openrouter.ai/rankings) rank *models* by tokens, with a
  "programming" category. There is no per-language breakdown **(unverified that none exists)**.
  The Anthropic Economic Index (https://huggingface.co/datasets/Anthropic/EconomicIndex) reports
  task and occupation shares, with no per-language series found **(unverified)**.
- **Reject reason:** not a per-language measure. This is a research gap (section 6): no public,
  per-language, AI-assistant-usage time series was found.

### Defunct

- **Stack Overflow Trends** (insights.stackoverflow.com/trends): retired; it redirects to the 2017
  launch post (verified).
- **LangPop (original, Dave Welton, about 2008–2013):** defunct **(unverified dates)**.
- **TLPI, Transparent Language Popularity Index (about 2010–2013):** defunct **(unverified dates)**.
- **Trendy Skills (job-ad based, about 2013–2016):** defunct **(unverified dates)**.
- **Kaggle ML & DS Survey:** ended after 2022 (see above).
- **hntrends.com:** unmaintained since May 2024.
- **GitHut 2.0:** unmaintained since April 2024.

---

## 5. Implications for the roadmap

### 5.1 Milestone 0001: the four planned providers

**Cross-cutting: granularity.** `Granularity` in `src/langrank/models.py` is only `YEAR` and
`MONTH`. Innovation Graph is quarterly, and RedMonk is irregular (currently stored as sparse
monthly). Add `QUARTER`, and consider `SNAPSHOT`/irregular, through a proper model change and
migration (append-only, per [CLAUDE.md](/CLAUDE.md)) before task 02.0. Do not encode quarters as
the first month of the quarter with `MONTH`: that would make quarterly data look like monthly data
and break the natural key's meaning.

**Task 01.0, `stackoverflow-tags`:**

- Endpoint:
  `GET https://api.stackexchange.com/2.3/questions?site=stackoverflow&tagged={tag}&fromdate={t0}&todate={t1}&filter=total`,
  one call per tag per month (verified working anonymously). Register an API key to get the daily
  quota. Store the key via config or env, never in the repo.
- Denominator options:
  - (a) all questions per month (`/search/advanced?...&filter=total`, verified), or
  - (b) questions with at least one tracked language tag. The API cannot OR-count de-duplicated
    across many tags in one call. A `tagged=a;b` call is an AND. Option (b) therefore needs dumps
    or SEDE.
  - **Recommendation:** use (a) as the documented denominator for the API variant. Offer (b) only
    through a dump-based variant. This contradicts the plan's "recommended default."
- The API returns current-state counts, so historical months drift as questions are deleted or
  re-tagged. Record `retrieved_at` and let changed `raw_record_hash` signal re-statements.
- Dumps: official downloads require login and an agreement barring LLM training. Community
  Internet Archive mirrors (`stackexchange_YYYYMMDD`, quarterly) exist. The legal gate must decide
  whether a dump-based variant is acceptable. SEDE is interactive and bot-protected, so it is not
  suitable for unattended fetch.
- Stack Overflow Trends is retired; do not target it.
- Expect very small monthly counts after 2024. Consider a validation warning when the
  denominator falls below a threshold, rather than silently presenting noisy shares.
- Tag map: `c++`, `c#`, `go` (SO tag is `go`; `golang` is a synonym), `objective-c`, `bash`,
  `shell`, `vba`, `vb.net`, `delphi`, `r`, and others. Resolve synonyms via `/tags/{tags}/synonyms`
  and record the synonym snapshot as a raw artifact.

**Task 02.0, `github` (Innovation Graph + Octoverse):**

- The Innovation Graph is **quarterly and per economy**, not annual as the plan's metrics table
  states. There is no global total. Summing `num_pushers` across economies gives a *lower bound*:
  economy-language cells under 100 developers are suppressed, and whether a developer can be
  counted in more than one economy is **unverified**. Any global figure is therefore derived.
  Flag it with `is_derived=True` and `derivation_method="sum_over_reported_economies"`, and keep
  the per-economy observations, or at least keep the list of economies summed, as provenance.
- Filter or tag `language_type` (`programming`/`markup`/`data`/`prose`). The published set changed
  in April 2025.
- Pin fetches to a release tag (for example `v1.0.11`) or commit SHA, so `source_document_id` is
  immutable.
- A per-economy dimension does not exist in the current natural key
  (`rating_id, metric_id, language_id, period_start, granularity`). Either encode the economy in
  `metric_id` (for example `pushers:US`) or add a dimension column via migration. Decide this
  before implementing.
- Octoverse offers no dataset. Treat it as manually curated annual top-N ranks with a
  per-edition metric-definition note: 2025 used distinct monthly contributors, August 2025
  snapshot, over a September–August window. Octoverse's "#1 by contributors" is not comparable
  with Innovation Graph pushers, and neither is comparable with RedMonk's GitHub axis.
- The plan's statement that GitHub's metric "is not interchangeable with RedMonk's" matters even
  more now: RedMonk's GitHub input is degraded after October 2025.

**Task 03.0, `ieee-spectrum`:**

- The profile names are **Spectrum / Jobs / Trending**. The plan's `default` corresponds to
  IEEE's "Spectrum."
- 2025 data is machine-readable via the Flourish embed
  (`https://flo.uri.sh/visualisation/24825595/embed`, `_Flourish_data`). Scores are normalized to
  top = 1. Store them as published and do not rescale to 100.
- Past editions are not preserved: `/top-programming-languages-2024` redirects to the current
  interactive. Historical backfill needs Wayback captures (capture timestamps become part of
  provenance), or manual transcription marked as such.
- About 51–53 of 64 tracked languages appear per profile. Absence means "not ranked," not zero.
- The 2026 edition is not out (404 at the expected slug). The provider must tolerate a missing or
  discontinued year.
- Methodology changes yearly (2025 switched to manual collection and added Discord), so version
  per edition with a `methodology_url` in provenance.

**Task 04.0, `jetbrains`:**

- Raw data is verified only for **2024 and 2025** at
  `resources.jetbrains.com/storage/products/research/DevEco{YEAR}/RawData.zip`. The plan's
  "historical from 2017 onward" is not achievable from raw data at a uniform URL. Earlier years
  require report-page values (manual or scraped) or discovering per-year raw-data URLs.
- The 2024 content license is **CC BY-NC-SA 4.0**. The legal gate must address NC and share-alike
  for cached artifacts and exported data.
- Raw microdata needs JetBrains' weighting to reproduce the published percentages, so re-tabulated
  values are derived. Prefer published report percentages as the non-derived observation.
- Populations shift: 2025 and 2026 are weighted toward professional developers. Record the
  population and weighting description as metadata, along with the exact question wording.
- The 2026 report (tenth edition, survey May–July 2026) is expected around Q4 2026 and is not yet
  verified as published.

**Legal / source-policy gate: facts to record.** SO content is CC BY-SA 4.0, the dump terms bar LLM
training, and the API has its own terms. Innovation Graph is CC0. SO Survey is ODbL/DbCL.
JetBrains 2024 is CC BY-NC-SA. IEEE and Octoverse have copyright only. PYPL is CC BY 3.0. TIOBE
allows attribution-only display, and its history is paid.

### 5.2 Existing providers: follow-ups surfaced by this research

1. `stackoverflow-survey`: switch to the official aggregated JSON
   (`packages/archive/{YEAR}/json/technology.json`, 2017–2025) with `total_respondents`
   denominators. Add `admired`/`desired` metrics (2023 and later) and subgroup metrics
   (professional versus all) as distinct metrics.
2. `pypl`: fetch `PYPL/All.js` directly. Expect whole-history re-statement each month.
3. `redmonk`: the cadence is now about annual, and the edition label lags publication by 3–6
   months. Annotate post-2025 editions with the SO-decline and GitHub-PR-anomaly caveats.
4. `tiobe`: archive the monthly HTML as raw artifacts to accumulate a first-party history.

### 5.3 Recommended backlog beyond 0001 (ranked)

1. **`stackoverflow-survey` v2** (JSON aggregates + admired/desired): an enhancement rather than a
   new provider. Highest value for the effort.
2. **`wikipedia-pageviews`** (P2): open, monthly since 2015-07, stable API, distinct
   "encyclopedic interest" signal. Needs a curated article-title map.
3. **`hn-hiring`** (P2): the only open, monthly, 2011-onward jobs signal. All values are
   LangRank-derived, so the derivation method has to be versioned.
4. **`github-linguist-search`** (P3): start forward snapshot collection now, since the value
   accrues only with time.
5. **`kaggle-survey`** (P3): a one-off static 2017–2022 import for a DS/ML population.
6. **`package-registries`** (P3): only as a separate ecosystem family, never as language
   popularity.
7. **`slashdata-communities`** (P3): manual transcription only, if licensing permits.

### 5.4 Sources to reject, with reasons

- **GitHut, Languish, GH Archive, OSS Insight:** all depend on GH Archive PR-language fields that
  GitHub removed on 2025-10-07. GitHut is stale and Languish is unlicensed. Innovation Graph
  supersedes them.
- **Google Trends:** redundant with PYPL, the API is gated alpha with a 5-year window, and
  scraping violates the ToS.
- **DevJobsScanner, HackerRank, CoderPad/CodinGame, LeetCode:** proprietary, not
  machine-readable, short series.
- **Indeed Hiring Lab:** openly licensed, but occupation-level, not per language.
- **Reddit subscribers:** removed from public view in September 2025; restrictive API.
- **Rosetta Code:** not a usage measure; no history.
- **LangPop (2026):** an aggregate of other indices (circular); unverifiable.
- **OpenRouter / Anthropic Economic Index:** not per language.

---

## 6. Research gaps and periodic re-verification (source-watch input)

### 6.1 Edition calendar

| Source | Cadence | Typical publication | Latest verified edition | Next expected | Watch signal |
|---|---|---|---|---|---|
| TIOBE | Monthly | First days of the month | September 2026 | Early October 2026 | Index page month header |
| PYPL | Monthly | About the 1st–10th of the month | September 2026 (commit 2026-09-10) | About 2026-10-10 | Commit to `PYPL/All.js` |
| RedMonk | About annual (was semiannual) | Irregular: "January" edition published April–June | January 2026 (published 2026-04-14) | A "June 2026" edition is uncertain | New post in the category feed |
| SO Developer Survey | Annual | Late June–July historically (2025: 2025-07-29) | 2025 | 2026 results: survey opened 2026-06-23, release date unverified (likely Q4 2026) | New `packages/archive/2026/` in `StackExchange/Survey` |
| SO data dumps (community mirror) | Quarterly | Data cut at quarter end; mirror 1–7 weeks later | `stackexchange_20260630` (posted 2026-08-17) | `stackexchange_20260930` around October–November 2026 | archive.org identifier search |
| SO API | Continuous | — | — | — | API version / quota changes |
| GitHub Innovation Graph | Quarterly | 3–4 months after quarter end | Q1 2026 (v1.0.11, 2026-07-07) | Q2 2026 around October–November 2026 | New release tag |
| GitHub Octoverse | Annual | Late October–early November (2025: 2025-10-28) | 2025 | Around late October 2026 | github.blog Octoverse category |
| IEEE Spectrum TPL | Annual | Late August–September (2021-08-24, 2022-08-23, about 2024-08-22, 2025-09-23) | 2025 | 2026 overdue: 404 as of 2026-09-24 | `/top-programming-languages-2026` status; Flourish embed ID change |
| JetBrains DevEco | Annual | October–December (2024-12-11; 2025 about October) | 2025 (raw ZIP 2025-10-16) | 2026 report around Q4 2026 | `DevEco2026/RawData.zip` turning 403 → 200 |
| SlashData language communities | About annual (biannual survey) | Varies | Q1 2026 (31st edition) | — | Report page edition text |
| Wikipedia pageviews | Daily | Month complete 1–2 days after month end | — | — | API schema / deprecation notices |
| HN "Who is hiring?" | Monthly | First weekday of the month | — | — | New `whoishiring` thread |
| Google Trends API | — | — | Alpha | GA announcement? | developers.google.com/search/apis/trends status |

### 6.2 Facts to re-verify periodically

- **GitHub Events API payloads.** Whether any language field returns, or further fields are
  removed. Affects RedMonk, GitHut, Languish, and IEEE's GitHub input.
- **Stack Exchange access policy.** Dump terms, SEDE availability and refresh cadence, API quota
  and terms (including any AI-use clauses, **unverified**), and the question-volume trend.
- **Innovation Graph schema.** `language_type` set, suppression threshold, new files, and any
  global aggregate.
- **IEEE Spectrum continuation.** Whether the 2026 edition appears or the ranking ends; profile
  names and embed format.
- **JetBrains licensing.** The 2025 and 2026 license wording (NC or not), and per-year raw-data URL
  discovery for 2017–2023.
- **SO Survey.** 2026 release date and schema (the 2026 survey was branded "for human developers
  only"); whether JSON aggregates continue.
- **RedMonk cadence and methodology.** Whether semiannual resumes, and whether SO is dropped or
  re-weighted.
- **TIOBE.** Any change to the engine list or methodology; price and availability of the history.
- **PYPL.** Language-set additions or removals (for example Zig) and regional file availability.

### 6.3 Open research gaps

- No public, per-language **AI-coding-assistant usage** time series was found (Copilot, Cursor,
  Claude Code, OpenRouter). Revisit as vendors publish.
- Exact per-edition metric definitions for **Octoverse** before 2022 **(unverified)**.
- Earliest **IEEE Spectrum** editions (2013–2020) and their data formats **(unverified)**.
- **JetBrains** raw-data availability and question wording by year **(unverified)**.
- Licenses for **Wikipedia pageviews** (believed CC0), the **HN API**, **Kaggle** survey data, and
  **crates.io** dumps **(unverified)**.
- Whether Innovation Graph developers can be counted in more than one economy, which affects any
  global sum **(unverified)**.
