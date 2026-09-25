# Providers

Providers implement the fetch -> parse -> normalize -> validate pipeline and must never write directly to SQLite.

See [/docs/source-notes/](/docs/source-notes/) for per-provider acquisition policy, quota limits, and terms notes.

## Demo provider

`demo` ships with LangRank and produces deterministic synthetic annual history for a small language set and two metrics:

- `rank`
- `rating`

The values are synthetic and intended only for testing, demos, and validating the architecture.

## Stack Overflow tags provider

**Rating ID:** `stackoverflow-tags`  
**Source note:** [/docs/source-notes/stackoverflow-tags.md](/docs/source-notes/stackoverflow-tags.md)  
**Threat model:** [/docs/security/2026-09-25-stackoverflow-tags-fetch.md](/docs/security/2026-09-25-stackoverflow-tags-fetch.md)

Measures monthly Stack Overflow question activity per language tag. This is **tag activity** (how many
questions are asked with a tag), which is a fundamentally different signal from
`stackoverflow-survey` (self-reported usage). The two must not be compared or combined without
explicit methodology documentation.

### Metrics

| Metric ID                                 | Unit    | Derived? | Notes                                                   |
|-------------------------------------------|---------|----------|---------------------------------------------------------|
| `stackoverflow-tags-questions`            | count   | No       | Raw monthly new-question count for the master tag.      |
| `stackoverflow-tags-question-share`       | percent | Yes      | Share of a stated denominator (see below).              |
| `stackoverflow-tags-rank`                 | rank    | Yes      | Competition rank on question-share within each month.   |

Derived metrics set `is_derived = True` on every `Observation`. The `derivation_method` field records
the exact derivation rule:

- Share: `question_share:all_questions` (api source) or `question_share:tracked_language_union` (sede source).
- Rank: `rank_by_question_share:all_questions` or `rank_by_question_share:tracked_language_union`.

### Acquisition mode (`--source`)

| Value  | Mode                  | Notes                                                                  |
|--------|-----------------------|------------------------------------------------------------------------|
| `api`  | Scheduled / automated | Queries Stack Exchange API v2.3 `filter=total` endpoint. Default.      |
| `sede` | Manual import only    | Operator runs a SEDE query and imports the resulting CSV.              |

`sede` cannot be used with `langrank fetch`; use `langrank import --rating stackoverflow-tags <csv>` instead.

### Denominators

The share denominator depends on the acquisition source. The two are **never mixed** in a single
series: every `Observation` records which denominator produced its share in `metadata_json`.

| Source | Denominator name           | Definition                                                                                           |
|--------|----------------------------|------------------------------------------------------------------------------------------------------|
| `api`  | `all_questions`            | Site-wide new-question total for the month, from a tag-free `filter=total` call.                     |
| `sede` | `tracked_language_union`   | Deduplicated union of questions carrying any tracked master tag (the SEDE query's `union_total` col). |

**Important:** because one question can carry multiple language tags, question-share values **may
sum above 100 %** across languages for a given month. This is expected and correct.

### API key and request budget

The provider reads the optional application key from the environment:

```
LANGRANK_STACKEXCHANGE_KEY=<your-key>
```

| Situation            | Daily request ceiling | Notes                                                    |
|----------------------|-----------------------|----------------------------------------------------------|
| Key set              | 5 000 req / day       | Well under the 10 000/day keyed quota; leaves headroom.  |
| No key (anonymous)   | 300 req / day         | Per-IP shared quota; not enough for a 10-year backfill.  |

The provider **calculates the planned request count before issuing any request** and raises
`FetchError` immediately if the plan would exceed the daily budget, naming the shortfall and
suggesting `--since`/`--until`/`--years` narrowing or setting `LANGRANK_STACKEXCHANGE_KEY`. No
partial fetches are started.

A 10-year backfill (`--years 10`) issues `months * (tags + 1)` requests (~3 700 for the default
tag set). This exceeds the anonymous budget of 300 requests/day, so a key is required. Alternatively
pass `--offline` to replay the newest cached artifact without any network calls.

### SEDE query template

To produce a manual import CSV for the `sede` source, run the following query in the
[Stack Exchange Data Explorer](https://data.stackexchange.com/stackoverflow/query/new):

```sql
-- Produces: month, tag, questions, union_total  (SEDE runs T-SQL / SQL Server)
-- union_total = COUNT(DISTINCT question) carrying ANY tracked master tag that month, so a
-- question tagged both python and c is counted once in the denominator (but once per tag in
-- `questions` - which is why per-language shares may sum above 100 %).
-- Replace the tag list to match TAG_TO_LANGUAGE in providers/stackoverflow_tags.py.
WITH tagged AS (
    SELECT p.Id AS PostId,
           CONVERT(char(7), p.CreationDate, 126) AS month,   -- 'YYYY-MM'
           t.TagName
    FROM Posts p
    JOIN PostTags pt ON pt.PostId = p.Id
    JOIN Tags     t  ON t.Id = pt.TagId
    WHERE p.PostTypeId = 1
      AND p.CreationDate < DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)  -- complete months only
      AND t.TagName IN (
          'python','java','javascript','typescript','c#','c++','c','php',
          'go','rust','kotlin','swift','ruby','r','scala','dart',
          'objective-c','perl','lua','haskell','elixir','julia','matlab',
          'sql','assembly','groovy','powershell','bash','vb.net',
          'fortran','cobol','ada','delphi','zig'
      )
),
per_tag AS (
    SELECT month, TagName AS tag, COUNT(DISTINCT PostId) AS questions
    FROM tagged
    GROUP BY month, TagName
),
per_month AS (
    SELECT month, COUNT(DISTINCT PostId) AS union_total
    FROM tagged
    GROUP BY month
)
SELECT pt.month, pt.tag, pt.questions, pm.union_total
FROM per_tag pt
JOIN per_month pm ON pm.month = pt.month
ORDER BY pt.month, pt.tag;
```

> Not yet executed against live SEDE (SEDE is login-gated); the query was reviewed for
> correctness of the distinct-union denominator only. SEDE also caps result rows (50 000), so run
> it per year range if needed.

Save the result as a CSV with columns `month,tag,questions,union_total` and import it:

```bash
uv run langrank import --rating stackoverflow-tags sede_export.csv
```

### Example commands

```bash
# Fetch the last 10 years via the API (requires LANGRANK_STACKEXCHANGE_KEY for a full backfill):
uv run langrank fetch stackoverflow-tags --years 10

# Replay from cache without network access:
uv run langrank fetch stackoverflow-tags --offline

# Plot question-share trend for four languages over the last 10 years:
uv run langrank plot --rating stackoverflow-tags \
    --metric stackoverflow-tags-question-share \
    --languages python,javascript,c++,rust \
    --years 10

# Export to CSV:
uv run langrank export csv --ratings stackoverflow-tags --since 2016 --output so_tags.csv
```

### Caveats

- Tag activity is not the same as language usage. A high question count means the language
  generates many Stack Overflow questions, not that it is widely used.
- Question-share sums may exceed 100 % because one question can carry multiple language tags.
- `api` and `sede` shares are **different series** with different denominators; do not mix them.
- Overall Stack Overflow question volume declined sharply after 2022; prefer question-share over
  raw counts for long-term trend comparison.
- The current (incomplete) calendar month is always excluded; the provider refuses to store data
  for it.

## GitHub provider

**Rating ID:** `github`  
**Source note:** [/docs/source-notes/github.md](/docs/source-notes/github.md)  
**Threat model:** [/docs/security/2026-09-25-github-fetch.md](/docs/security/2026-09-25-github-fetch.md)

GitHub language popularity is exposed through two **independent** variants selected with `--source`.
The variants are never conflated with each other, and neither is comparable with RedMonk's
GitHub-derived component (RedMonk plots a GitHub pull-request rank vs. Stack Overflow tag rank
composite; see [/docs/source-notes/redmonk.md](/docs/source-notes/redmonk.md)).

| Variant             | `--source` value                  | Granularity | Signal                           |
|---------------------|-----------------------------------|-------------|----------------------------------|
| Innovation Graph    | `innovation-graph` or `auto`      | Quarterly   | Derived global pusher counts     |
| Octoverse           | `octoverse`                       | Annual      | Raw published top-languages rank |

`--source auto` resolves to `innovation-graph`. The two variants own separate metric IDs, so a
query or plot can never silently mix them.

### Metrics

| Metric ID                              | Unit    | Derived? | Notes                                                          |
|----------------------------------------|---------|----------|----------------------------------------------------------------|
| `github-octoverse-rank`                | rank    | No       | Raw published annual top-languages rank (1 is best).           |
| `github-innovation-graph-pushers`      | count   | Yes      | Quarterly global pusher count, derived by summing per-economy cells. |
| `github-innovation-graph-share`        | percent | Yes      | Share of total published-language pushers for the quarter.     |
| `github-innovation-graph-rank`         | rank    | Yes      | Competition rank on global pusher share (1 is best).           |

Derived metrics set `is_derived = True` on every `Observation`. The `derivation_method` field
records the exact derivation rule:

- `github-innovation-graph-pushers`: `sum_over_economies:suppressed_below_100`
- `github-innovation-graph-share`: `share_of_all_published_language_pushers`
- `github-innovation-graph-rank`: `rank_by_global_pushers`

### Acquisition mode (`--source`)

| Value                   | Mode                   | Notes                                                                    |
|-------------------------|------------------------|--------------------------------------------------------------------------|
| `auto` / `innovation-graph` | Scheduled / automated | Fetches from GitHub's `innovationgraph` repository at a pinned SHA. Default. |
| `octoverse`             | Manual curation only   | Reads a bundled CSV; issues no network requests.                         |

`langrank fetch all` fetches only the `innovation-graph` variant. Octoverse data is bundled in the
repository and requires no network fetch.

### Innovation Graph: derived-value semantics

All three Innovation Graph metrics are derived. Their derivation chain:

1. **Pusher count** (`github-innovation-graph-pushers`,
   `derivation_method="sum_over_economies:suppressed_below_100"`): each per-economy cell from
   `github/innovationgraph/data/languages.csv` records the count of distinct developers making a
   push from that economy in that quarter. Cells with fewer than **100 developers** are suppressed
   by GitHub before publication, so the global sum is a systematic **undercount biased against
   small languages**; this shortfall is recorded in `derivation_method` and never corrected or
   interpolated.
2. **Share** (`github-innovation-graph-share`,
   `derivation_method="share_of_all_published_language_pushers"`): the pusher count divided by the
   total pushers across **all** published Linguist language names that quarter, including unmapped
   and non-language names (e.g. `Dockerfile`, `HTML`). The denominator therefore includes entries
   that are not stored, which keeps shares comparable across quarters even as the set of mappable
   languages changes.
3. **Rank** (`github-innovation-graph-rank`, `derivation_method="rank_by_global_pushers"`):
   competition rank on the global share, computed over **mapped languages only** (standard
   competition ranking: equal shares share a rank; the next rank skips tied positions).

A developer active in two economies in one quarter is counted once per economy by GitHub's data;
global sums therefore **may double-count multi-economy developers**. This is documented as a caveat
and never corrected.

The `population` field on every derived Innovation Graph observation is
`"global (economies ≥100 developers)"`.

### Commit-SHA pinning and reproducibility

Online fetches issue exactly **two requests** (≤2 per fetch):

1. One request to `api.github.com` (the commits API) to resolve the latest commit SHA touching
   `data/languages.csv`. The optional `GITHUB_TOKEN` is read from the environment and sent
   **only as an `Authorization` header on this request**; it is never embedded in a URL, cache
   file, or log.
2. One request to `raw.githubusercontent.com` to download the CSV at the pinned SHA. The token is
   **never sent to this host**.

The commit SHA is validated to exactly 40 lowercase hex digits before being interpolated into the
download URL. The downloaded bytes' sha256 and the commit SHA are stored in the artifact metadata
and in a `.meta` sidecar next to the cached CSV, enabling `--offline` replay with integrity
re-check.

### Octoverse editions

Octoverse data is **manually curated** from published text and tables; no network request is issued
and chart-pixel extraction is not implemented. Requesting `--source octoverse-chart` raises a
`ProviderError`.

| Edition        | Basis                  | Ranks captured                             |
|----------------|------------------------|--------------------------------------------|
| 2025           | `monthly_contributors` | 1-3 (numbered in prose and alt text)       |
| 2024           | `contributors`         | 1-10 (numbered labels in chart alt text)   |
| 2023 and earlier | -                    | Omitted - prose states at most #1-#2; remainder is chart-only or unordered |

Ranks 4+ for the 2025 edition appear only as an unordered "other top languages include ..." list
and are omitted, not guessed. For the 2024 edition, the numbered labels
(`Python (1)` ... `Go (10)`) in the ranking chart's published alt text are ruled to be published
text, not chart-geometry extraction. For the full alt-text ruling and per-edition source URLs, see
[/docs/source-notes/github.md](/docs/source-notes/github.md).

The ranking basis changes between editions, so annual Octoverse ranks are not directly comparable
year-over-year without consulting each edition's `ranking_basis` field. One `MethodologyNote` per
distinct basis records the span of editions that used it.

Granularity is `Granularity.YEAR` for Octoverse and `Granularity.QUARTER` for Innovation Graph.
See [/docs/data-model.md#granularity](/docs/data-model.md#granularity) for period label formats.

### GITHUB_TOKEN and rate limits

| Situation           | Hourly ceiling   | Notes                                           |
|---------------------|------------------|-------------------------------------------------|
| No token (anonymous)| 60 req / hour    | Anonymous rate limit for `api.github.com`.      |
| `GITHUB_TOKEN` set  | 5 000 req / hour | Token sent as `Authorization: Bearer` only.     |

At ≤2 requests per fetch the unauthenticated ceiling is far above a normal schedule. The provider
refuses to start if the planned request count would exceed the applicable ceiling.

### Example commands

```bash
# Fetch the last 5 years of Innovation Graph data (default source):
uv run langrank fetch github --years 5

# Fetch only the Octoverse variant (reads bundled CSV, no network):
uv run langrank fetch github --source octoverse

# Plot Innovation Graph pusher share for three languages over 5 years:
uv run langrank plot --rating github \
    --metric github-innovation-graph-share \
    --languages python,typescript,rust \
    --years 5

# Plot the derived rank:
uv run langrank plot --rating github \
    --metric github-innovation-graph-rank \
    --languages python,typescript,rust \
    --years 5

# Query Octoverse ranks:
uv run langrank query --rating github --metric github-octoverse-rank --language python

# Replay from cache without network access:
uv run langrank fetch github --offline
```

### Caveats

- This is not RedMonk's GitHub component. RedMonk combines GitHub pull-request rank with Stack
  Overflow tag rank; this provider is a separately sourced, independently maintained measure.
- The `octoverse` and `innovation-graph` variants measure different things and are never conflated.
- Innovation Graph global pusher counts are an **undercount**: GitHub suppresses any
  economy/language cell with fewer than 100 developers, biasing against smaller languages.
- A developer active in multiple economies in one quarter is counted once per economy; global sums
  may therefore **double-count multi-economy developers**.
- The share denominator includes unmapped and non-language Linguist names; shares will not sum to
  100 % over mapped languages alone, but are comparable across quarters.
- Octoverse ranking basis is not constant across editions; ranks are not directly comparable
  year-over-year without consulting `ranking_basis`.
- Only ranks printed in Octoverse text or tables are captured; chart-pixel extraction is not
  implemented.
- `fetch all` fetches only the Innovation Graph variant; Octoverse is bundled in the repository.

## IEEE Spectrum provider

**Rating ID:** `ieee-spectrum`
**Source note:** [/docs/source-notes/ieee-spectrum.md](/docs/source-notes/ieee-spectrum.md)
**Gate verdict:** `manual-only` — 0 network requests; no automated or unattended fetch.

IEEE Spectrum publishes an annual *Top Programming Languages* composite index. Each edition
re-weights one metric set into several ranking **profiles**; a language's rank and score are
meaningful only **within one profile of one edition**. This provider stores each profile as its
own metric pair so a query never mixes profiles into one series.

> **Profiles are distinct rankings, never one series.** Do not plot or compare
> `ieee-spectrum-spectrum-*`, `ieee-spectrum-jobs-*`, and `ieee-spectrum-trending-*` on a shared
> axis. Editions are not comparable either: the score is renormalized per edition and the metric
> set and weights change between editions.

Data comes from a manually transcribed, repo-committed bundled CSV
(`src/langrank/providers/data/ieee_spectrum.csv`), read at `fetch` time with 0 network requests.
There is no downloadable or machine-readable dataset from IEEE; the acquisition mechanism is
manual transcription only. For the acquisition policy, score-scale rationale, Flourish data file
ruling, terms, and robots.txt status see the [source note](/docs/source-notes/ieee-spectrum.md).

### Profiles

| Profile    | Description                                                              |
|------------|--------------------------------------------------------------------------|
| `spectrum` | Default; weighted for typical IEEE members / working software engineers. |
| `jobs`     | Employer demand.                                                         |
| `trending` | Zeitgeist (trend-signal weighting).                                      |

The three profiles are verified for the 2022-2025 editions and map 1:1 onto the pre-2022
interactive presets of the same name. The pre-2022 `Open` and `Custom` presets have no stable
cross-edition definition and are **not imported**. Every profile is its own metric pair;
querying one profile never returns another profile's rows.

### Metrics

All six metric IDs follow the scheme `ieee-spectrum-{profile}-{rank|score}`.

| Metric ID                         | Unit  | Derived? | Notes                                                    |
|-----------------------------------|-------|----------|----------------------------------------------------------|
| `ieee-spectrum-spectrum-rank`     | rank  | Yes      | Competition rank derived from published scores (1 = best). |
| `ieee-spectrum-spectrum-score`    | score | No       | Published relative score, stored as-is.                  |
| `ieee-spectrum-jobs-rank`         | rank  | Yes      | Competition rank derived from published scores (1 = best). |
| `ieee-spectrum-jobs-score`        | score | No       | Published relative score, stored as-is.                  |
| `ieee-spectrum-trending-rank`     | rank  | Yes      | Competition rank derived from published scores (1 = best). |
| `ieee-spectrum-trending-score`    | score | No       | Published relative score, stored as-is.                  |

### Score scale (edition-specific, never rescaled)

The published score is relative within each edition: the top-ranked language equals the scale's
maximum value. Scores are **not** comparable across editions for two compounding reasons: the
score is renormalized per edition (top = max), and the metric set and weights change between
editions.

| Editions  | Scale | Top value |
|-----------|-------|-----------|
| 2022      | 0-100 | `100`     |
| 2023-2025 | 0-1   | `1`       |

Scores are stored exactly as published; no rescaling or cross-edition normalization is applied.
Score observations are `is_derived=False`.

### Derived ranks

IEEE's published data file has no rank column. Ranks are computed by this project from the
published scores using standard competition ranking: equal scores share a rank and the next
rank is skipped (ties do not raise an error). Rank observations are `is_derived=True` with
`derivation_method="rank_by_published_score"`.

See [/docs/data-model.md#derived-observations](/docs/data-model.md#derived-observations) for
the `is_derived` / `derivation_method` field semantics.

### Acquisition mode

| Mode          | Network requests | How triggered                                          |
|---------------|-----------------|--------------------------------------------------------|
| Bundled CSV   | 0               | `langrank fetch ieee-spectrum` or `langrank fetch all` |
| Manual import | 0               | `langrank import --rating ieee-spectrum <csv>`         |

`langrank fetch ieee-spectrum` reads the curated bundled CSV committed at
`src/langrank/providers/data/ieee_spectrum.csv`. The `--source` flag accepts `auto` (default)
or `bundled`; any other value is rejected. No unattended or scheduled fetch exists for this
source.

### Adding a future edition

When a new IEEE Spectrum edition is published, transcribe the ranks and scores from the
published article or Flourish data file and import them:

```bash
uv run langrank import --rating ieee-spectrum path/to/new_edition.csv
```

**Required CSV header** (all columns are required; column order does not matter):

```
year,profile,rank,language,score,source_url,published_at,methodology_version
```

| Column                | Format / notes                                                                                  |
|-----------------------|-------------------------------------------------------------------------------------------------|
| `year`                | 4-digit calendar year, e.g. `2026`.                                                             |
| `profile`             | One of `spectrum`, `jobs`, or `trending`.                                                       |
| `rank`                | Positive integer; pre-compute from published scores using competition ranking (see above).       |
| `language`            | Exact IEEE label as it appears in the edition's data file.                                      |
| `score`               | Published relative score; may be empty if no score is available for the row.                    |
| `source_url`          | Canonical `spectrum.ieee.org` URL for the edition (not a Wayback snapshot URL).                 |
| `published_at`        | Edition publication date in `YYYY-MM-DD` format.                                                |
| `methodology_version` | Short stable identifier for the edition, e.g. `ieee-2026-7metrics`.                            |

**New-edition checklist:**

- [ ] Transcribe ranks and scores from the published Flourish data file (or article
      table/prose if no data file is available).
- [ ] Pre-compute competition ranks from the published scores (equal scores share a rank; the
      next rank skips tied positions); record them in the `rank` column.
- [ ] Check for and drop duplicate language rows (see the ABAP defect in the
      [source note](/docs/source-notes/ieee-spectrum.md)); other ranks remain as computed.
- [ ] Add a row to the editions table in
      [/docs/source-notes/ieee-spectrum.md#editions](/docs/source-notes/ieee-spectrum.md#editions).
- [ ] Add a `_Edition` entry to `IEEE_EDITIONS` in `src/langrank/providers/ieee_spectrum.py`
      (year, methodology version, source URL, description of any metric-set changes).
      `EDITION_PROFILES` is derived from `IEEE_EDITIONS` automatically.
- [ ] Add the new year's score scale to `SCORE_SCALE_BY_YEAR` in the same file if the scale
      changed from the previous edition.
- [ ] Append the new rows to `src/langrank/providers/data/ieee_spectrum.csv` and commit.

### Untracked labels

The following IEEE labels are intentionally not tracked — they do not raise an
`unmapped_language` warning and produce no observation:

| Label           | Reason                                                                                    |
|-----------------|-------------------------------------------------------------------------------------------|
| `HTML`          | Markup language, not a programming language.                                              |
| `Arduino`       | Hardware platform, not a language.                                                        |
| `Verilog`       | Hardware description language.                                                            |
| `VHDL`          | Hardware description language.                                                            |
| `Visual Basic`  | Classic VB. Splitting it from `vb.net` is deferred: the global alias `"visual basic" → vb.net` would merge them. |
| `Cuda`          | C++ dialect / GPU-programming API, not a distinct language.                               |
| `WebAssembly`   | Compilation target, not a source language.                                                |
| `LabView`       | Graphical/PLC programming environment.                                                    |
| `Ladder Logic`  | Graphical/PLC programming environment.                                                    |
| `Pascal/Delphi` | IEEE 2022-2023 combined category; mapping it to either `pascal` or `delphi` would merge  |
|                 | two distinct languages.                                                                   |

Any other IEEE label that does not map to a canonical language is recorded as an
`unmapped_language` warning and produces no observation.

### Example commands

```bash
# Fetch the bundled curated edition data (no network requests):
uv run langrank fetch ieee-spectrum

# Plot the Spectrum profile rank for three languages over 10 years:
uv run langrank plot --rating ieee-spectrum \
    --metric ieee-spectrum-spectrum-rank \
    --languages python,java,c++ \
    --years 10

# Plot the Jobs profile rank:
uv run langrank plot --rating ieee-spectrum \
    --metric ieee-spectrum-jobs-rank \
    --languages python,sql,javascript \
    --years 5

# Query the Trending profile score for Python:
uv run langrank query --rating ieee-spectrum \
    --metric ieee-spectrum-trending-score \
    --language python

# Export all IEEE Spectrum metrics to CSV:
uv run langrank export csv --ratings ieee-spectrum --since 2022 --output ieee_spectrum.csv

# Import a new edition from a manually transcribed CSV:
uv run langrank import --rating ieee-spectrum path/to/2026_edition.csv
```

### Caveats

- Profiles are different rankings produced by re-weighting one metric set. They must not be
  merged into a single series or plotted on one shared axis.
- Editions are not comparable: scores are renormalized per edition and the metric set and
  weights change between editions. Even an unchanged metric set would not make cross-edition
  scores comparable because of per-edition renormalization.
- The 2022 edition uses a 0-100 score scale; 2023-2025 use 0-1. Do not compare raw scores
  across these editions.
- Rank is derived (computed from published scores by this project, not published by IEEE).
- The 2025 `Trending` list contained `ABAP` twice with different scores; both rows were
  dropped as ambiguous. Other ranks in that edition are computed over the list as published.
- Acquisition is manual transcription only: all data comes from the bundled curated CSV or a
  manually imported file. No automated or unattended fetch exists for this source.
- Coverage is limited to ranks and scores IEEE actually publishes. Where only a top-N is shown,
  ranks beyond N stay missing (no interpolation, no fabricated values).
- For terms, robots.txt status, and the full Flourish data file acquisition ruling see the
  [source note](/docs/source-notes/ieee-spectrum.md).
