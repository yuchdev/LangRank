# ieee-spectrum test fixtures

Fixtures for the `ieee-spectrum` provider contract tests. Tests never hit the
network: IEEE Spectrum publishes **no downloadable dataset** (its `robots.txt`
disallows scraping the interactive app), so the repo-committed, manually
transcribed CSV `src/langrank/providers/data/ieee_spectrum.csv` **is** the
source. These fixtures are a small, verbatim subset of that bundled CSV.

## `sample.csv`

A **verbatim** subset of `src/langrank/providers/data/ieee_spectrum.csv`. Every
row below is copied byte-for-byte from the bundled dataset (same columns,
`year,profile,rank,language,score,source_url,published_at,methodology_version`);
**no cell was hand-edited or fabricated.** The provider derives ranks and treats
scores as published raw, so keeping the rows verbatim keeps the golden honest.

### Selection rule

The Cartesian slice of:

- **2 editions with different published-score scales:** `2022` (scale `0-100`)
  and `2024` (scale `0-1`). This pins the contract that each edition's score
  scale is preserved and never rescaled across editions.
- **All 3 profiles:** `spectrum`, `jobs`, `trending` (every imported profile), so
  the "profiles are never merged into one series" guarantee can be checked.
- **5 languages:** `Python`, `C++`, `Ada`, `Haskell` (all map to canonical
  language ids) plus `HTML` — a documented
  `langrank.normalization.IEEE_UNTRACKED_LABELS` markup label that must produce
  **no observation and no `unmapped_language` warning**.

Every `(edition × profile)` group is present for all 5 languages (30 rows), so
`HTML` appears once per group (6 rows) and never becomes an observation.

### Competition-ranking tie

The `2024 jobs` edition lists `Ada` and `Haskell` **tied at rank 44 with an equal
score (`0`)** — a genuine standard-competition-ranking tie copied verbatim.
Because their scores are equal, the shared rank is legitimate and
`validate` must **not** raise `duplicate_rank` (only a shared rank with *differing*
scores is an error).

### Missing-score case

Every bundled row carries a score, so this fixture file contains no empty-score
row. The "empty `score` yields a rank observation but never a fabricated score
observation" contract is exercised in-test by appending a single synthetic
empty-score row to the parsed payload (mirroring the in-test synthetic row used
by `tests/fixtures/github/SOURCE.md`), leaving this checked-in fixture 100 %
verbatim.

## `expected_observations.json`

Golden normalized output produced by the provider's `parse` -> `normalize` and
serialized by `tests/contract/_golden.py` (`retrieved_at` stripped; sorted by
`metric_id, language_id, period_start`). Contains 48 observations: 4 mapped
languages × 6 `(edition × profile)` groups × 2 metrics (rank + score); `HTML`
contributes none. Regenerate after an intentional change with
`LANGRANK_UPDATE_GOLDEN=1` and review the diff before committing. A changed
golden means a changed observation — never regenerate to silence an unexpected
diff.
