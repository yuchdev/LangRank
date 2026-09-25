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
