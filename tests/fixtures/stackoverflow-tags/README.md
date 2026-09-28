# stackoverflow-tags test fixtures

Fixtures for the `stackoverflow-tags` provider contract tests. Tests never hit
the network; these are the checked-in inputs and golden output.

## `api_sample.json`

Real aggregate counts captured **live** from the Stack Exchange API v2.3.

- Source: `GET https://api.stackexchange.com/2.3/questions`
  with `site=stackoverflow&filter=total&tagged={tag}&fromdate={epoch}&todate={epoch}`
  (one `filter=total` call per tag per month, plus one no-tag call per month for
  the `all_questions` denominator).
- Capture date: **2026-09-25** (unauthenticated, no app key; well under the
  ~300 requests/day anonymous quota; `backoff` honoured).
- Window: months `2024-01`, `2024-02`, `2024-03`; tags `python`, `javascript`,
  `java`, `go`, `rust`; plus each month's site-wide `total`.
- Content: aggregate question counts only. No question bodies, titles, IDs or any
  user-contributed content is stored (`filter=total` returns just `{"total": N}`).

## `sede_sample.csv`

Hand-built fixture in the documented SEDE export shape
(`month,tag,questions,union_total`), not a live capture. It deliberately encodes
the two edge cases the spec requires:

- A **multi-tag month** whose per-language shares sum above 100 % (a question
  carrying two tracked tags is counted under each): `600 + 500 + 300` questions
  against a deduplicated `union_total` of `1000` → shares `60 + 50 + 30 = 140 %`.
  This is documented behaviour, not a validation error.
- A **renamed tag**: the `golang` row must normalize to canonical language `go`
  via the `stackoverflow-tags` rating-scoped alias.

## `expected_observations.json`

Golden normalized output for `api_sample.json`, produced by the provider's
`parse` -> `normalize` and serialized by `tests/contract/_golden.py`
(`retrieved_at` stripped; sorted by `metric_id, language_id, period_start`).
Regenerate after an intentional change with `LANGRANK_UPDATE_GOLDEN=1` and review
the diff before committing.
