# Providers

Providers implement the fetch -> parse -> normalize -> validate pipeline and must never write directly to SQLite.

See [/docs/source-notes/](/docs/source-notes/) for per-provider acquisition policy, quota limits, and terms notes.

## Provider contract

Every provider implements the `RatingProvider` protocol (`src/langrank/providers/base.py`) with
five methods: `metadata()`, `fetch(request)`, `parse(payload)`, `normalize(records)`, and
`validate(observations)`. Providers must never write to SQLite; persistence is the service
layer's responsibility via `Database`.

### Optional capability: SupportsRawImport

`SupportsRawImport` (`src/langrank/providers/base.py`) is an additional, optional,
runtime-checkable protocol for providers that must ingest a large, untrusted, operator-supplied
local file under explicit size and row caps:

```python
class SupportsRawImport(Protocol):
    def import_path(self, path: Path) -> list[SourceRecord]:
        """Stream path and return the parsed source records (capped, no full read)."""
        ...
```

`langrank import` dispatches at runtime via `isinstance(provider, SupportsRawImport)`:

- **Provider implements `SupportsRawImport`:** the CLI calls `provider.import_path(path)`. The
  method owns all streaming, size-capping, CSV-robustness, and parsing logic. The default
  whole-file `path.read_bytes()` → `provider.parse()` path is **not** used for this provider.
- **Provider does not implement `SupportsRawImport`:** the CLI calls `path.read_bytes()` and
  passes the bytes to `provider.parse()` (existing behaviour, unchanged).

The `jetbrains` provider currently implements `SupportsRawImport` because the JetBrains raw-data
dump is hundreds of MB uncompressed and must not be loaded into memory whole (see
[JB-SEC-1](/docs/security/2026-09-26-jetbrains-import.md)).

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

## JetBrains Developer Ecosystem provider

**Rating ID:** `jetbrains`
**Source note:** [/docs/source-notes/jetbrains.md](/docs/source-notes/jetbrains.md)
**Threat model:** [/docs/security/2026-09-26-jetbrains-import.md](/docs/security/2026-09-26-jetbrains-import.md)
**Gate verdict:** `manual-only` for both modes — 0 automated network requests.

JetBrains runs an annual *State of Developer Ecosystem* survey (first edition 2017) and
publishes **weighted** language-usage figures. This provider stores three metrics that are
**never merged**: past-12-month usage, primary language, and planned adoption. These are
distinct questions on different denominators and must not be plotted or compared on a
shared axis.

Two acquisition modes exist and own separate metric families:

- **published** (default): reads JetBrains' own **weighted** percentages from a bundled
  curated CSV (`src/langrank/providers/data/jetbrains.csv`); `is_derived=False`; 0 network
  requests.
- **raw-data** (import): operator imports the anonymized response dump; LangRank computes
  **unweighted** respondent shares; `is_derived=True`; `-raw` metric IDs.

> **Weighted and unweighted values are not comparable and never share a series.**
> Each published metric and its `-raw` counterpart are permanently separate series.
> `primary_language` and `used_last_12_months` answer **different** survey questions on
> different denominators and are never merged. Shares **may sum above 100 %** because the
> usage and planned-adoption questions are multi-select; the 2017 primary-language question
> was single-choice, so its values do sum to 100 %.

**Data origin (published values):** every percentage in the bundled CSV (723 rows, 2017-2025)
comes from chart data JetBrains ships with each rendered edition page — chart configurations
bundled in the page bundle (2017, 2018) or data files on `resources.jetbrains.com` (2019-2025).
No value was estimated from bar length or pixel geometry. The used-last-12-months history was
cross-checked against JetBrains' own multi-year retrospective charts (2021-2025 editions):
648 year × language comparisons, 2 disagreements (`2022 HTML/CSS` 55 vs 54 and `Lua` 4 vs 3 —
the edition's own data-file values are kept). See the
[source note](/docs/source-notes/jetbrains.md) for the full acquisition narrative and gate ruling.

### Metrics

| Metric ID | Unit | Derived? | Acquisition mode | Notes |
|---|---|---|---|---|
| `jetbrains-used-last-12-months` | percent | No | published | JetBrains' weighted %; multi-select (may sum >100 %). |
| `jetbrains-primary-language` | percent | No | published | JetBrains' weighted %; single-choice in 2017, up to 3 from 2019. |
| `jetbrains-planned-adoption` | percent | No | published | JetBrains' weighted %; multi-select (may sum >100 %). |
| `jetbrains-used-last-12-months-raw` | percent | Yes | raw-data import | Unweighted respondent share; `derivation_method="unweighted_respondent_share"`. |
| `jetbrains-primary-language-raw` | percent | Yes | raw-data import | Unweighted respondent share; `derivation_method="unweighted_respondent_share"`. |
| `jetbrains-planned-adoption-raw` | percent | Yes | raw-data import | Unweighted respondent share; `derivation_method="unweighted_respondent_share"`. |

Published metrics store `is_derived=False`. Raw (`-raw`) metrics store `is_derived=True` with
`derivation_method="unweighted_respondent_share"`. Raw values differ from JetBrains' published
weighted figures and are never presented as equivalent.

See [/docs/data-model.md#derived-observations](/docs/data-model.md#derived-observations) for
the `is_derived` / `derivation_method` field semantics.

### Question wording registry

The provider maintains a `QUESTION_REGISTRY` (`src/langrank/providers/jetbrains_questions.py`)
with one `SurveyQuestion` entry per survey year and metric. Each observation carries the
question it answers in `metadata_json["question_wording"]`.

Wording discipline: only the **verbatim** question text JetBrains actually published is stored
as verified wording (`wording_verified=True`); chart legends and group headings are kept
separately as `chart_legend` and **never** treated as question wording. When JetBrains'
verbatim string has not been confirmed for a year, `wording=None` and `wording_verified=False`
— wording is never invented. A `MethodologyNote` is emitted for each confirmed wording change
between consecutive verified years; unverified years are skipped in change detection so
fabricated wording never feeds a methodology note.

Currently verified verbatim wordings:

| Year | Metric | Verified verbatim wording |
|------|--------|---------------------------|
| 2018 | used-last-12-months | "What programming language(s) do you regularly use?" |
| 2018 | planned-adoption | "Do you plan to adopt / migrate to other language(s) in the next 12 months? If so, to which one(s)?" |
| 2019 | used-last-12-months | "What programming languages have you used in the last 12 months?" |
| 2019 | primary-language | "What are your primary programming languages? Choose no more than 3 languages." |
| 2023 | used-last-12-months | "Which programming, scripting, and markup languages have you used in the last 12 months?" |
| 2024 | used-last-12-months | "Which programming languages have you used in the last 12 months?" |

### Coverage

| Year | used-last-12-months | primary-language | planned-adoption | Notes |
|------|---------------------|-----------------|-----------------|-------|
| 2017 | Yes | Yes (single-choice) | Yes | "used regularly" wording; all three wording unverified. |
| 2018 | Yes | **Omitted** | Yes | Primary rendered as rank podium only — no percentages published. |
| 2019 | Yes | Yes | Yes | |
| 2020 | Yes | Yes | Yes | |
| 2021 | Yes | Yes | Yes | |
| 2022 | Yes | Yes | Yes | |
| 2023 | Yes | Yes | Yes | |
| 2024 | Yes (top-20 only) | Yes | Yes | Usage published only as a top-20 history chart. |
| 2025 | Yes (top-20 only) | Yes | Yes | Planned adoption: all rows from data file (chart shows top 5). |

`sample_size` is the edition's total respondent count; JetBrains publishes no per-question
counts. 2017 and 2018 totals are approximate ("over 5,000", "6,000") and those editions do
not state weighting methodology.

### Acquisition modes

| Mode | Network requests | How triggered |
|------|-----------------|---------------|
| `published` (bundled CSV) | 0 | `langrank fetch jetbrains` or `langrank fetch all` |
| `raw-data` (manual import) | 0 | `langrank import --rating jetbrains <raw.csv>` |

`langrank fetch jetbrains` reads the curated bundled CSV with 0 network requests. The
`--source` flag accepts `auto` (default), `published`, or `raw-data`; passing `raw-data` to
`fetch` raises `NotImplementedError` — use `langrank import` instead.

### Raw-data import

The operator obtains the anonymized response dump out-of-band (LangRank makes no automated
download), extracts the CSV from the zip, and runs:

```bash
uv run langrank import --rating jetbrains /path/to/raw.csv
```

**Edition downloads and licences:**

| Year | Raw data | Licence |
|------|----------|---------|
| 2025 | [`DevEco2025/RawData.zip`](https://resources.jetbrains.com/storage/products/research/DevEco2025/RawData.zip) (~98 MB) | CC BY-NC-SA 4.0 — non-commercial, share-alike, attribution required |
| 2024 | [`DevEco2024/RawData.zip`](https://resources.jetbrains.com/storage/products/research/DevEco2024/RawData.zip) (~87 MB) | CC BY-NC-SA 4.0 — non-commercial, share-alike, attribution required |
| 2023 | [Google Drive folder](https://drive.google.com/drive/folders/1w-uI4-G2eWn_eqUe69IoT8McuJCENB3O) (browser; no login) | Attribution-only |
| 2022 | [Google Drive folder](https://drive.google.com/drive/folders/1nlvy45tE4gFX_oWNxG_UTC1-tLZBTcbR) (browser; no login) | Attribution-only |
| 2017-2021 | None published | n/a |

**Only the 2024 raw layout is supported for import.** The 2025 dump reuses identical
column-name prefixes (`proglang::`, `primary_lang::`, `adopt_proglang::`), making year
detection permanently ambiguous; `import` rejects 2025 files with a clear error. 2022 and
2023 raw layouts have not yet been transcribed into the question registry.

**Import limits** (per [JB-SEC-1..3](/docs/security/2026-09-26-jetbrains-import.md)):

| Limit | Value | Reason |
|-------|-------|--------|
| Max file size | 600 MB | Byte cap; checked via `st_size` before any read. |
| Max rows | 2,000,000 | Row cap during streaming parse. |
| Max line length | 16 MiB | Per-line cap before full row materialisation. |
| Max columns | 50,000 | Header column count cap. |
| File type | Regular file only | FIFOs / char-devices report `st_size = 0` and bypass the byte cap. |
| Zip files | Rejected | Pre-extract the CSV first; 4-byte magic check rejects zip. |

**What is stored:** only per-language aggregate counts and the respondent denominator
(`sample_size` and `metadata["denominator"]`). Language columns are identified by the survey
year's `QUESTION_REGISTRY` column-name prefixes; every other column — including free-text
answers — is ignored and never persisted. Raw files (zip or extracted CSV) are **never written
to the repo, shared cache, or any published location**; they stay on the operator's local disk
only. Test fixtures are tiny synthetic rows; no verbatim JetBrains response data is committed.

**Licence obligations for `-raw` series:** the derived series carry the source licence in
release metadata. CC BY-NC-SA 4.0 (2024/2025) restricts commercial use and requires
share-alike attribution. Do not redistribute raw data or `-raw` derived values commercially.

### Example commands

```bash
# Fetch the bundled published (weighted) percentages (no network):
uv run langrank fetch jetbrains

# Plot used-last-12-months for three languages over 10 years (published, weighted):
uv run langrank plot --rating jetbrains \
    --metric jetbrains-used-last-12-months \
    --languages python,java,kotlin \
    --years 10

# Plot primary language over 8 years:
uv run langrank plot --rating jetbrains \
    --metric jetbrains-primary-language \
    --languages python,java,kotlin \
    --years 8

# Import the 2024 raw dump (extract DevEco2024/RawData.zip first):
uv run langrank import --rating jetbrains /path/to/2024_sharing_data_outside.csv

# Query the unweighted (raw) used-last-12-months series:
uv run langrank query --rating jetbrains \
    --metric jetbrains-used-last-12-months-raw \
    --language python

# Export all JetBrains metrics to CSV:
uv run langrank export csv --ratings jetbrains --since 2017 --output jetbrains.csv
```

### Caveats

- `used_last_12_months`, `primary_language`, and `planned_adoption` are **different questions**
  on different denominators. Never merge or plot them on a shared axis.
- Published (weighted) and raw (unweighted) values are not comparable; they are permanently
  separate metric IDs and must never share a series.
- Shares **may sum above 100 %** because usage and planned-adoption are multi-select; the 2017
  primary-language question was single-choice.
- 2018 primary language is omitted (no published percentages; rendered as a rank podium only).
- 2024 and 2025 usage lists are top-20 only; languages outside the top 20 stay missing.
- Only the 2024 raw-dump layout is supported for import. 2025 is refused (ambiguous year
  detection); 2022/2023 layouts are not yet transcribed.
- Raw imports are local-file-only with no automated download. Raw files must never be
  committed to the repo, shared cache, or published exports.
- JetBrains corrects for audience skew (JetBrains-tool users are down-weighted), but the
  correction is editorial. See the [source note](/docs/source-notes/jetbrains.md) for details.
- Acquisition is manual-only in both modes (0 automated network requests). `langrank fetch all`
  fetches only the published bundled CSV; raw-data import requires a separate `langrank import`
  call.
