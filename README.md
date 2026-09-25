# LangRank

`langrank` is a Python CLI application for collecting, normalizing, storing, querying, exporting, and plotting historical programming-language ranking signals from multiple sources.

## Purpose

LangRank is designed to bring together different programming-language popularity indicators into one local, queryable SQLite database while preserving source-specific semantics and provenance.

## Important methodological warning

Future sources do **not** measure the same thing, so their scores should not be treated as interchangeable estimates of one true popularity score.

- TIOBE -> search/web visibility
- PYPL -> tutorial-search interest
- RedMonk -> GitHub + Stack Overflow activity
- GitHub -> development/repository activity
- SO Survey -> self-reported usage
- SO Tags -> questions/discussion
- IEEE Spectrum (`ieee-spectrum`) -> composite weighted index (profiles: spectrum / jobs / trending)
- JetBrains -> survey-reported usage

## Installation

```bash
uv sync
```

## Providers

The application now includes working providers for:

- `tiobe`
- `pypl`
- `redmonk`
- `stackoverflow-survey`
- `stackoverflow-tags` - monthly question activity per language tag (see [docs/providers.md](/docs/providers.md))
- `github` - Innovation Graph quarterly pusher data and Octoverse annual rankings (see [docs/providers.md](/docs/providers.md))
- `ieee-spectrum` - annual Top Programming Languages bundled composite-index, 3 profiles × 6 metrics (see [docs/providers.md](/docs/providers.md))
- `jetbrains` - annual State of Developer Ecosystem survey, 3 published metrics + 3 raw-import metrics (see [docs/providers.md](/docs/providers.md))
- `demo` (synthetic offline dataset for development)

```bash
uv run langrank fetch all --years 10
uv run langrank query --rating tiobe --language python --years 10
uv run langrank plot --rating redmonk --metric rank --languages python,c++,rust --years 10
uv run langrank plot --rating stackoverflow-tags --metric stackoverflow-tags-question-share \
    --languages python,javascript,c++,rust --years 10
uv run langrank export csv --ratings tiobe,pypl,redmonk,stackoverflow-survey,stackoverflow-tags \
    --since 2016 --output history.csv
uv run langrank plot --rating ieee-spectrum --metric ieee-spectrum-spectrum-rank \
    --languages python,java,c++ --years 10
uv run langrank plot --rating jetbrains --metric jetbrains-used-last-12-months \
    --languages python,java,kotlin --years 10
```

> **Note:** `stackoverflow-tags` measures question-asking activity, not language usage - it is a
> different signal from `stackoverflow-survey` (self-reported usage) and must not be treated as
> equivalent. A full 10-year backfill requires `LANGRANK_STACKEXCHANGE_KEY`; use `--offline` to
> replay a cached artifact without network access. See
> [docs/providers.md](/docs/providers.md) for quota details.

> **Note:** `ieee-spectrum` stores three independent ranking profiles (`spectrum`, `jobs`,
> `trending`) as separate metrics. Profiles and editions are **not** comparable with each other;
> do not plot them on a shared axis. Data comes from a bundled curated CSV with 0 network
> requests. See [docs/providers.md](/docs/providers.md) for the full metric table and
> new-edition import guide.

> **Note:** `jetbrains` stores three published (weighted) metrics and three raw-import
> (unweighted) counterparts. The three metrics (`used_last_12_months`, `primary_language`,
> `planned_adoption`) are different survey questions and must never be merged or plotted on a
> shared axis. Shares may sum above 100 % (multi-select). Bundled published data requires 0
> network requests; raw-data import requires the operator to download the anonymized dump
> out-of-band. See [docs/providers.md](/docs/providers.md) for the full metric table, import
> limits, and licence obligations.

## Development checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
