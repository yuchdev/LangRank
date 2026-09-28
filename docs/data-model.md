# Data model

The canonical row is an observation: one metric for one language from one rating/source for one historical period.

Primary persistent entities:

- `ratings`
- `languages`
- `language_aliases`
- `metrics`
- `observations`
- `fetch_runs`
- `raw_artifacts`

Observation upserts are deterministic on `(rating_id, metric_id, language_id, period_start, granularity)`.

## Derived observations

Some metrics are not directly published by the source but are computed from raw values by the
provider's `normalize()` step. Every derived observation records two fields that distinguish it from
source-published data:

- `is_derived` (`bool`) - `True` for any value that was calculated, not read from the source.
- `derivation_method` (`str | None`) - human-readable label naming the computation rule, e.g.
  `question_share:all_questions` or `rank_by_question_share:tracked_language_union`.

Derived values **must never be presented as source data**. Validators enforce that `is_derived` is
set on every metric that the provider registers as derived (see the `share_not_derived` validation
code in `stackoverflow-tags`).

Example: the `stackoverflow-tags` provider publishes raw question counts (`is_derived=False`) and
then derives monthly question-share percentages (`is_derived=True`,
`derivation_method="question_share:all_questions"`) and ordinal ranks (`is_derived=True`,
`derivation_method="rank_by_question_share:all_questions"`). See
[/docs/providers.md](/docs/providers.md) for the full metric table.

## Granularity

Every observation carries a `granularity` value that describes the time resolution of its period.
The `period_label` format follows from the granularity:

| `Granularity` | `period_label` format | Example  | Notes                                       |
|---------------|-----------------------|----------|---------------------------------------------|
| `year`        | `YYYY`                | `2024`   | `period_start` = Jan 1; `period_end` = Dec 31. |
| `quarter`     | `YYYY-Qn`             | `2024-Q3`| `period_start` = first day of the quarter; `period_end` = last day. Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec. |
| `month`       | `YYYY-MM`             | `2024-09`| `period_start` = first day of the month; `period_end` = last day. |

`Granularity.QUARTER` is used by the `github` Innovation Graph variant. `Granularity.YEAR` is used
by the `github` Octoverse variant and annual survey providers. `Granularity.MONTH` is used by
monthly providers such as `stackoverflow-tags`.

Observations with different granularities should not be plotted on the same axis without explicit
resampling.
