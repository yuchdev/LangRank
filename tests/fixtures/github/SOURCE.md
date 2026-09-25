# github test fixtures

Fixtures for the `github` provider contract tests (both variants:
`innovation-graph` and `octoverse`). Tests never hit the network; these are the
checked-in inputs and golden outputs.

## `innovation_graph_languages.csv`

A **real** slice of the GitHub Innovation Graph `data/languages.csv`, captured
**live** and then trimmed. This dataset is **CC0-1.0**.

- Source repo: <https://github.com/github/innovationgraph>
- Pinned commit SHA: **`054c7dbc527518fa2ecfd316efe2aa01f3986c39`**
  (resolved via `GET https://api.github.com/repos/github/innovationgraph/commits?path=data/languages.csv&per_page=1`,
  one unauthenticated request; that commit was authored 2026-07-07).
- Raw source URL:
  `https://raw.githubusercontent.com/github/innovationgraph/054c7dbc527518fa2ecfd316efe2aa01f3986c39/data/languages.csv`
  (downloaded once, unauthenticated: 2 requests total, within the anonymous
  GitHub REST ceiling).
- Capture date: **2026-09-25**.
- Header preserved **exactly** as published, including the extra `language_type`
  column the live file now carries
  (`num_pushers,language,language_type,iso2_code,year,quarter`); the provider
  only reads its required columns and tolerates the extra one.

### Trimming rule

The 180k-row file was filtered to the Cartesian slice of:

- **2 quarters:** `2025-Q4`, `2026-Q1` (the two most recent complete quarters);
- **3 economies:** `US`, `IN`, `BR` (`iso2_code`);
- **6 Linguist names:** `Python`, `JavaScript`, `C++` (mapped), plus
  `Jupyter Notebook` and `HTML` (documented `GITHUB_NON_LANGUAGES`, excluded from
  the language series but kept in the share denominator) and `Solidity` (a real
  Linguist language absent from this project's canonical catalog, so it surfaces
  as an `unmapped_language` warning).

All 36 cells (2 × 3 × 6) are present at the pinned commit — no `>=100`-developer
suppression gaps in this slice — so every `num_pushers` value below is the
unmodified published figure. **No rows were hand-edited or fabricated.**

## `octoverse.csv`

A subset of the repo's bundled curated Octoverse rankings CSV
(`src/langrank/providers/data/github_octoverse.csv`), same documented shape
(`year,rank,language,ranking_basis,source_url,published_at`). Two editions with
**different ranking bases**: 2024 top-5 (`contributors`) and 2025 top-3
(`monthly_contributors`). Ranks stay contiguous `1..n` within each edition. These
ranks are transcribed from the Octoverse report text/tables (no chart pixel
extraction); the per-edition `source_url` and `published_at` are the published
values.

## `expected_innovation_graph.json` / `expected_octoverse.json`

Golden normalized output produced by the provider's `parse` -> `normalize` and
serialized by `tests/contract/_golden.py` (`retrieved_at` stripped; sorted by
`metric_id, language_id, period_start`). Regenerate after an intentional change
with `LANGRANK_UPDATE_GOLDEN=1` and review the diff before committing. A changed
golden means a changed observation — never regenerate to silence an unexpected
diff.
