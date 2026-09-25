# JetBrains - State of Developer Ecosystem

JetBrains runs an annual *State of Developer Ecosystem* survey (first edition 2017) and publishes
**weighted** language-usage figures. This provider exposes three metrics that are **never merged**:
`jetbrains-used-last-12-months`, `jetbrains-primary-language`, `jetbrains-planned-adoption`
(see [plan.md § Task 04.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-040---jetbrains-developer-ecosystem-provider)).
Two acquisition modes exist and are governed by **separate** gate verdicts below:
`published` (bundled curated CSV of JetBrains' published, weighted percentages) and `raw-data`
(user-supplied import of the anonymized response dump, from which LangRank computes **unweighted**
respondent shares stored under distinct `-raw` metric IDs).

- What it measures: self-reported programming-language usage/intent, **weighted** by JetBrains to
  their estimate of the global professional-developer population. `used_last_12_months` (past-12-month
  usage) is the most consistently asked question since 2017; `primary_language` (main language) and
  `planned_adoption` (planning to adopt/migrate to) are distinct questions on distinct denominators.
- Official source: annual infographic/report pages on `www.jetbrains.com/lp/devecosystem-<year>/`
  (2025 moved to `devecosystem-2025.jetbrains.com`); per-edition methodology pages (e.g.
  <https://lp.jetbrains.com/developer-ecosystem-2025-methedology/>,
  <https://www.jetbrains.com/lp/devecosystem-2024/>).
- Published-value shape: the infographic pages are JavaScript-rendered SPAs; the language
  percentages are presented **as charts/images**, not as a downloadable text/HTML/CSV/JSON table
  (verified for 2024/2025 - "presented only as images"). There is therefore **no machine-readable
  published dataset**; `published` values are hand-transcribed into a curated bundled CSV
  (`src/langrank/providers/data/jetbrains.csv`), each row carrying `source_url`. Only the bare
  factual percentages plus the edition URL are stored - never the infographic images or prose.
- Weighting (published = weighted): JetBrains applies a multi-stage weighting (regional
  professional-developer population, employment-status normalization, then a language/product-usage
  calibration solved as "a system of 30+ linear equations and inequalities" via the Goldfarb-Idnani
  dual method; JetBrains-user over-representation down-weighted). Published percentages are therefore
  **weighted** and stored `is_derived=False` (they are JetBrains' own numbers, not derived by us).
- Raw-data mode (derived): over the anonymized `RawData` dump, LangRank computes **unweighted**
  per-language respondent shares - `is_derived=True`,
  `derivation_method="unweighted_respondent_share"`, metric IDs suffixed `-raw` (e.g.
  `jetbrains-used-last-12-months-raw`). These differ from JetBrains' published weighted figures and
  **never share a series** with the `published` metrics.
- Acquisition mechanism: **manual-only for both modes.** `published` reads the bundled CSV at
  `fetch()` (0 network requests). `raw-data` is `langrank import --rating jetbrains <raw.csv>` over a
  file the operator has already obtained out-of-band; LangRank performs **no automated download** of
  the raw dump (2022/2023 dumps live behind Google Drive folders needing browser navigation;
  2024/2025 are large direct-download zips). No scraping of the SPA, no chart-pixel/geometry
  extraction.
- Published-data origin (curated 2026-09-26, 36 slow single requests, ruling in
  [status.md](/docs/roadmap/0001-new-rating-providers/status.md#notes--decisions)): every value in
  `providers/data/jetbrains.csv` (723 rows, 2017-2025) comes from the chart data JetBrains ships with
  a rendered chart - chart configs in the page bundle (2017, 2018) or the report's data files on
  `resources.jetbrains.com` / the edition's `/_data/*.csv` (2019-2025). No value was read from bar
  length. The used-last-12-months history was cross-checked against JetBrains' own multi-year
  retrospective charts (2021-2025 editions): 648 year × language comparisons, 2 disagreements
  (2022 `HTML / CSS` 55 vs 54 and `Lua` 4 vs 3 - the edition's own values are kept).
- Coverage caveats: 2017/2018 "used" is labelled "used regularly" (JetBrains' later retrospective
  series reproduces those values as "used in the last 12 months"); 2018 planned adoption only offered
  languages *not* already selected as used; primary language is single-choice in 2017 and "up to 3"
  from 2019; 2018 primary is omitted (podium graphic without percentages); 2024/2025 usage is
  published only as a top-20 history; 2025 planned adoption includes all rows of the chart's data
  file although the chart displays the top five. `sample_size` is the edition's total respondent
  count (JetBrains prints no per-question counts); 2017/2018 totals are approximate ("over 5,000",
  "6,000") and those editions do not state weighting.
- Survey year vs period: `period` = survey year; `source_published_at` = report publication date
  (e.g. the 2025 survey ran Apr-Jun 2025, published later in 2025).
- Language normalization rules: map each JetBrains language label to the canonical language via the
  rating-scoped alias map (subtask 02/03); preserve the source string in the `SourceRecord`; unmapped
  labels become `unmapped_language` warnings and produce no `Observation`. Multi-select answers are
  counted per selected language; no synthetic splits/merges.
- Known limitations: audience skews toward JetBrains-tool users (JetBrains corrects for this in its
  weighting, but the correction is editorial); question wording and answer sets drift year to year
  (tracked per year in the edition table and `metadata_json["question_wording"]`, with a
  `MethodologyNote` on change). Weighted vs unweighted figures are not comparable and are kept in
  separate metric IDs.
- Fallbacks: none. Missing years/languages stay missing; no interpolation, no cross-edition carry.

## robots.txt / crawl policy (verified 2026-09-26)

- `www.jetbrains.com/robots.txt`: a real file with `User-Agent: *` and path-specific `Disallow`
  rules (`*/search/`, `*/shop/`, `/languages/`, `*/feedback/`, storefront paths). **No global
  `Disallow: /`** and **no AI-agent-specific block** (no `ClaudeBot`/`anthropic-ai`/`GPTBot`/`CCBot`
  stanzas). The survey report path `/lp/devecosystem-*` is **not** disallowed. (`/languages/` - the
  product-language pages - is disallowed, but that is unrelated to the survey.)
- `lp.jetbrains.com/robots.txt`: **no robots.txt** (host returns a 404 SPA page); no declared
  crawl restrictions.
- `devecosystem-2025.jetbrains.com/robots.txt`: **no robots.txt** (host serves the Next.js SPA for
  all paths); the app pages carry `<meta name="robots" content="noindex">` (indexing discouraged)
  but no path-level crawl disallow and no AI-agent block.
- **No AI agents are disallowed** on any of the three hosts, and no path this provider touches is
  disallowed. The provider is nonetheless **manual-only** by design (below); it issues no
  unattended crawl regardless.

## Editions

`raw_data_terms`: **CC-BY-NC-SA-4.0** = Creative Commons Attribution-NonCommercial-ShareAlike 4.0;
**attribution-only** = "public report, contents may be used as long as the source is appropriately
credited". Sizes are HEAD-only (`Content-Length`); zips were **not** downloaded.

| year | report_url | raw_data_url | raw_data_terms | respondents (cleaned) | published_at | language question(s) shown |
|------|-----------|--------------|----------------|-----------------------|--------------|----------------------------|
| 2025 | <https://devecosystem-2025.jetbrains.com/> | <https://resources.jetbrains.com/storage/products/research/DevEco2025/RawData.zip> (98,301,992 B; HTTP 200; Last-Modified 2025-10-16; no form/login) | CC-BY-NC-SA-4.0 | 24,534 (194 countries) | 2025 (Oct) | used last 12 months; primary; planning to adopt |
| 2024 | <https://www.jetbrains.com/lp/devecosystem-2024/> | <https://resources.jetbrains.com/storage/products/research/DevEco2024/RawData.zip> (87,173,442 B; HTTP 200; Last-Modified 2024-12-13; no form/login) | CC-BY-NC-SA-4.0 | 23,262 | 2024 (Dec) | "Which programming languages have you used in the last 12 months?"; primary; planning to adopt |
| 2023 | <https://www.jetbrains.com/lp/devecosystem-2023/> | Google Drive folder <https://drive.google.com/drive/folders/1w-uI4-G2eWn_eqUe69IoT8McuJCENB3O> (browser navigation; no login) - **not** at the `DevEco2023/RawData.zip` path (that path returns HTTP 403) | attribution-only | 26,348 (196 countries) | 2023 (Nov) | past-12-month usage; primary; planning to adopt |
| 2022 | <https://www.jetbrains.com/lp/devecosystem-2022/> | Google Drive folder <https://drive.google.com/drive/folders/1nlvy45tE4gFX_oWNxG_UTC1-tLZBTcbR> (browser navigation; no login) - first raw-data release, announced at <https://blog.jetbrains.com/blog/2023/03/13/developer-ecosystem-survey-2022-discover-raw-data/> - **not** at the `DevEco2022/RawData.zip` path (HTTP 403) | attribution-only | ~29,000 | 2022 | past-12-month usage; primary; planning to adopt |
| 2021 | <https://www.jetbrains.com/lp/devecosystem-2021/> | none published | n/a | 31,743 (183 countries) | 2021 | used last 12 months; main language; planning to adopt/migrate to |
| 2020 | <https://www.jetbrains.com/lp/devecosystem-2020/> | none published | n/a | ~19,700 | 2020 | used last 12 months; main; planning to adopt |
| 2019 | <https://www.jetbrains.com/lp/devecosystem-2019/> | none published | n/a | ~7,000 | 2019 | used last 12 months; main; planning to adopt |
| 2018 | <https://www.jetbrains.com/lp/devecosystem-2018/> | none published | n/a | ~6,000 | 2018 | used last 12 months; main; planning to adopt |
| 2017 | <https://www.jetbrains.com/lp/devecosystem-2017/> | none published | n/a | ~5,000 | 2017 | used regularly (≙ used last 12 months); primary language (single-choice); to be adopted / migrated to soon |

Notes on the table: exact per-year question wording is only reproduced verbatim by JetBrains in some
methodology pages (2024 confirms *"Which programming languages have you used in the last 12
months?"*); other years frame the same "past 12 months" question but do not print the verbatim string
on the methodology page - subtask 02 records the exact wording per year from each report as it is
transcribed, and flags any year with "no comparable language question" rather than fabricating one.
Respondent counts for 2017-2022/2020-2018 marked `~` are approximate pending per-edition confirmation
in subtask 02; 2023/2024/2025 counts are methodology-page verified.

## Gate

- **Gate verdict - `published` mode: `manual-only` (curation).** Reviewer: Security Auditor agent.
  Date: 2026-09-26. Values are JetBrains' published **weighted** percentages, hand-transcribed from
  the image/chart infographics into the bundled CSV; `is_derived=False`; each row carries `source_url`
  and the edition's licence. Conditions: no network fetch (bundled CSV read at `fetch()`); no
  chart-pixel/geometry extraction; store only the bare percentages + `source_url` + attribution,
  never the infographic images or prose. Satisfies the milestone
  [legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
  for this mode without a network threat model.
- **Gate verdict - `raw-data` mode: `manual-only` (import).** Reviewer: Security Auditor agent.
  Date: 2026-09-26. Download requires a browser/Google-Drive form (2022/2023) or a large manual
  direct download (2024/2025); LangRank performs **no automated download**. The `langrank import`
  path ingests a large, untrusted, user-supplied file and is **security-sensitive** - see the
  threat model [/docs/security/2026-09-26-jetbrains-import.md](/docs/security/2026-09-26-jetbrains-import.md)
  (JB-SEC-1..9). Values are LangRank-derived **unweighted** shares, `is_derived=True`, `-raw` metric
  IDs. This mode clears the gate **only** once the threat model's HIGH requirements (streaming/size
  caps, CSV robustness, PII/free-text exclusion, no-redistribution) are implemented in subtask 06.
- **Request budget:** `published` = **0 network requests** (bundled CSV). `raw-data` = **0 automated
  network requests** by LangRank (operator downloads out-of-band; `import` reads a local file). The
  verification for this gate used **7 slow, single, rate-limited requests** (3 `robots.txt` GETs + 4
  `HEAD`s on the 2022-2025 RawData.zip URLs; zips never downloaded), plus out-of-band
  WebSearch/WebFetch metadata reads.
- **Licence consequences (raw data, esp. 2024/2025 CC BY-NC-SA 4.0 - NonCommercial + ShareAlike +
  Attribution):**
  - Release/dataset metadata for any `-raw` series **must carry** the source licence
    (`CC-BY-NC-SA-4.0` for 2024/2025; attribution string for 2022/2023) and attribution, propagated
    into the dataset release workflow
    ([0004 Task 02.0](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md)).
    NonCommercial and ShareAlike restrict downstream reuse of derived values.
  - Raw files (zip or extracted CSV) are **never redistributed, never committed** to the repo, and
    **never copied into any shared/published cache** - they stay in the operator's **local** cache
    dir only. Test fixtures must be tiny **synthetic** samples, never verbatim JetBrains raw rows.
  - Published-figure infographics are likewise **not** redistributed; only the bare factual
    percentages + `source_url` + attribution are stored.
- **Last verified date: 2026-09-26.**
- Parser/version notes: `jetbrains-v1` (published) / `jetbrains-raw-v1` (import).
</content>
</invoke>
