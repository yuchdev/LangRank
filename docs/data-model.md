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
