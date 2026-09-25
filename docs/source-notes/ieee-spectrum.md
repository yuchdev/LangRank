# IEEE Spectrum - Top Programming Languages

IEEE Spectrum publishes an annual *Top Programming Languages* (TPL) study. Each edition produces
**several rankings ("profiles") from one metric set by re-weighting** - a language's rank and score
are only meaningful *within one profile of one edition*. This provider stores each profile as its own
metric pair and never merges profiles (or editions) into a single comparable series
(see [plan.md § Task 03.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-030---ieee-spectrum-provider)).

- What it measures: a composite, weighted popularity **index** built by IEEE from multiple raw
  signals (Google search, Stack Overflow / Stack Exchange questions, IEEE Xplore articles, IEEE Jobs
  Site + CareerBuilder postings, GitHub activity, Trinity College Dublin library holdings, Discord
  servers). Each raw metric is normalized to 0-1, multiplied by a per-profile weight, combined, and
  renormalized; the published **score is relative, with the top-ranked language = 100** and lower
  languages scaled to it (verified in the 2019 article and unchanged in wording since). It is
  explicitly not a cross-source "popularity" figure and is stored `is_derived=False` (it is IEEE's
  own published number, not something this project derives).
- Official source: the annual article + interactive app on `spectrum.ieee.org`; the per-edition
  methodology page (e.g. <https://spectrum.ieee.org/top-programming-languages-methodology-2025>,
  <https://spectrum.ieee.org/top-programming-languages-methodology-2024>). There is **no downloadable
  or machine-readable dataset**: the interactive ranking app is JavaScript-rendered in the browser and
  IEEE ships no CSV/JSON/API export. Since the 2024/2025 editions IEEE itself gathers the underlying
  data **manually** because of "API changes and terminations" and language-name collisions.
- Historical availability: annual since 2014; the 2023 edition was the 10th. Interactive editions
  exist through 2021 (e.g. <https://spectrum.ieee.org/top-programming-languages-interactive-2021/>,
  <https://spectrum.ieee.org/the-top-programming-languages-2019>); 2022 onward settled on the three
  named profiles below. The curated dataset (subtask 04) imports the editions listed in the table.
- Acquisition mechanism: **manual transcription only** (`manual_transcription`) into a curated bundled
  CSV `src/langrank/providers/data/ieee_spectrum.csv`, plus the existing
  `langrank import --rating ieee-spectrum <csv>` path for future editions. No network fetch, no
  scraping of the interactive app, no chart-pixel/geometry extraction. Only the bare ranks and scores
  IEEE prints (in article prose/tables or the rendered app) are transcribed, each row carrying its
  `source_url`; article prose, images, and charts are never copied.
- Data origin (curated 2026-09-26; 9 user-directed requests in a first prose-only pass, then one
  re-read per 2022-2025 edition article): each edition article
  embeds a Flourish visualisation whose **published data file** carries, per profile
  (`Spectrum`/`Jobs`/`Trending`), every language label and IEEE's `Score`. Reading that data file
  counts as published text (ruling in
  [status.md](/docs/roadmap/0001-new-rating-providers/status.md#notes--decisions)); the per-language
  `Description` prose in the same file is IEEE copyright and is **not** stored. The 2023 and 2024
  article URLs now redirect to the 2025 edition, so they were read from Wayback snapshots
  (`web.archive.org/web/20231230112038id_/…/the-top-programming-languages-2023`,
  `web.archive.org/web/20241025122520id_/…/top-programming-languages-2024`); `source_url` keeps
  the canonical spectrum.ieee.org URL.
- Score scale (**edition-specific, stored exactly as published, never rescaled**): 2022 data file
  uses 0-100 (top = `100`); 2023-2025 use 0-1 (top = `1`). Scores are not comparable across editions
  anyway (per-edition renormalization).
- Ranks are **derived**: IEEE's data file has no rank column, so `rank` is computed from the
  published scores within each edition × profile (competition ranking - ties share a rank, the next
  rank is skipped). Rank observations are `is_derived=True`,
  `derivation_method="rank_by_published_score"`; score observations are raw (`is_derived=False`).
- Source data defect: the 2025 `Trending` list contains `ABAP` twice with different scores
  (0.00943391 and 0.00942475). Both ABAP rows are dropped as ambiguous; other languages keep the
  ranks computed over the list as published.
- Imported metrics: `ieee-spectrum-{profile}-rank` and `ieee-spectrum-{profile}-score` for each
  published profile (`spectrum`, `jobs`, `trending`) - e.g. `ieee-spectrum-jobs-rank`,
  `ieee-spectrum-trending-score`. `spectrum` is IEEE's own label for the default (IEEE-member-weighted)
  profile - plan.md's `default` maps to `spectrum` here. Every profile is a **distinct metric**;
  querying one profile must never return another profile's rows, and profiles/editions are never
  plotted on one shared axis.
- Profiles: `spectrum` (default; weighted for typical IEEE members / working software engineers),
  `jobs` (employer demand), `trending` (zeitgeist). These three names are verified for the 2022-2025
  editions. Pre-2022 interactive editions instead exposed presets named *Spectrum* (default),
  *Trending*, *Jobs* and *Open* (open-source interest) plus a *Custom* slider view. **Decision (this
  gate):** for any pre-2022 edition, import only the `spectrum`/`jobs`/`trending` presets, which map
  1:1 to the modern profile IDs; the *Open* and *Custom* presets have no stable cross-edition
  definition and are **not imported** (noted per edition in `coverage`).
- Granularity: annual (`Granularity.YEAR`); one edition per calendar year.
- Coverage: only ranks/scores IEEE actually publishes for an edition/profile are stored. Where the app
  shows the full list (~55-64 languages) it is transcribed in full; where only a top-N is published,
  ranks beyond N stay **missing** (no interpolation, no fabricated values).
- Language normalization rules: map each IEEE language label to the canonical language via the
  rating-scoped alias map (subtask 02); preserve the source string in the `SourceRecord`. **Standing
  decision:** the IEEE labels `HTML`, `Arduino`, `Verilog` and `VHDL` are **not** canonical
  programming languages for this project (markup / hardware-platform / hardware-description labels) and
  are routed to `IEEE_UNTRACKED_LABELS` (implemented in subtask 02) - they are recognised so they do
  not raise `unmapped_language`, but they produce no `Observation`. Other unmapped labels become
  `unmapped_language` warnings recorded in metadata. No synthetic splits or merges.
- Methodology versions & comparability: the metric set and weights **change between editions**, so
  scores and ranks are **not comparable across editions** and only comparable *within* one edition's
  one profile. Verified metric-set breaks: **11 metrics from 8 sources** (2019-era), **8 metrics /
  8 sources** (2024), **7 metrics / 8 sources over 64 languages** (2025); the 2022 edition redesigned
  the profile presentation. Because the score is renormalized per edition (top = 100), even an
  unchanged metric set would not make cross-edition scores comparable. One `MethodologyNote` is
  recorded per edition (`methodology_notes` table) with the metric count/source changes; the CSV
  parser is versioned only if the CSV format changes.
- Known limitations: weighting is IEEE's editorial choice and is described by IEEE itself as
  "subjective"; the 2025 edition flags a large collapse in Stack Exchange question volume (~22% of
  2024's), which shifts scores independently of real language usage - a further reason not to compare
  scores across editions. The index reflects search/discussion/jobs/library/repo signals, not code
  volume or deployed usage.
- Fallbacks: none. Missing ranks/scores stay missing; no interpolation, no synthetic totals, no
  cross-edition carry-forward.
- Terms/automation considerations: IEEE holds copyright on Spectrum article text, tables, and figures;
  reuse of the **article content** requires permission via IEEE / the Copyright Clearance Center
  (RightsLink) - see <https://www.ieee.org/publications/rights/reqperm> and
  <https://www.ieee.org/publications/rights/copyright-policy>. Bare factual ranks and scores are not
  themselves copyrightable, so this provider stores **only** those facts plus the edition URL and an
  attribution string ("Data from IEEE Spectrum Top Programming Languages, © IEEE; see <source_url>"),
  never the prose, tables-as-text, or images. `spectrum.ieee.org/robots.txt` (verified 2026-09-25)
  additionally `Disallow: /` for generic and AI-training crawlers, including `ClaudeBot` and
  `anthropic-ai`, which independently rules out automated crawling of the app - reinforcing the
  manual-only posture below.
- Redistribution: store ranks + scores (facts) + `source_url` + attribution only. No raw-artifact
  (article/app) redistribution; no caching of page HTML.
- Gate verdict: **`manual-only`** - reviewer: Security Auditor agent - date: 2026-09-25. Conditions:
  no network acquisition and no scraping of the interactive app; ranks/scores transcribed from
  published text/tables or the rendered app only; chart-pixel/geometry extraction refused; each
  profile stored as a distinct metric and never compared across profiles or editions; article prose
  and figures never copied; IEEE attribution + `source_url` recorded on every row.
- Request budget: **0 network requests** - the curated bundled CSV is read at `fetch()` time (same
  pattern as the Octoverse / TIOBE bundled-CSV providers). No scheduled/unattended fetch exists for
  this source, so the milestone's
  [legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
  is satisfied by this manual-only note without a separate threat model.
- Parser/version notes: `ieee-spectrum-v1`.
- Last verified date: 2026-09-25.

## Editions

| year | url | profiles | coverage | methodology_version | notes |
|------|-----|----------|----------|---------------------|-------|
| 2025 | <https://spectrum.ieee.org/top-programming-languages-2025> | spectrum, jobs, trending | full list (64 languages) where app shows it; else published top-N | `ieee-2025-manual-7metrics` | Published 2025-09-23. 7 metrics / 8 sources, manually gathered (API terminations). Stack Exchange question volume ~22% of 2024. |
| 2024 | <https://spectrum.ieee.org/top-programming-languages-2024> | spectrum, jobs, trending | full list where shown; else top-N | `ieee-2024-manual-8metrics` | 8 metrics / 8 sources, data gathered manually to avoid API bias and name collisions. |
| 2023 | <https://spectrum.ieee.org/the-top-programming-languages-2023> | spectrum, jobs, trending | full list where shown; else top-N | `ieee-2023-8metrics` | 10th annual edition. Spectrum #1 Python; Jobs #1 SQL. Metric count not re-confirmed this pass - confirm exact count when transcribing. |
| 2022 | <https://spectrum.ieee.org/top-programming-languages-2022> | spectrum, jobs, trending | full list where shown; else top-N | `ieee-2022-profile-redesign` | Profile presentation redesigned to the three named profiles. Confirm URL + metric set when transcribing. |
| 2021 | <https://spectrum.ieee.org/top-programming-languages-interactive-2021/> | spectrum, jobs, trending (Open/Custom presets not imported) | JS-rendered interactive app; transcribe presets shown | `ieee-2019-11metrics-8sources` | Interactive edition; 11 metrics / 8 sources era. Only spectrum/jobs/trending presets imported. Optional for the initial dataset. |

Editions before 2021 (2014-2019 interactive apps) use the same 11-metric / 8-source family and the
Spectrum/Trending/Jobs/Open/Custom presets; they are out of scope for the initial curated dataset and
can be added later via `langrank import` following the decisions in this note. Every year the curated
dataset (subtask 04) actually imports must appear as a row above before import.
