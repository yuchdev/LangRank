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
- IEEE -> composite index
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
- `demo` (synthetic offline dataset for development)

```bash
uv run langrank fetch all --years 10
uv run langrank query --rating tiobe --language python --years 10
uv run langrank plot --rating redmonk --metric rank --languages python,c++,rust --years 10
uv run langrank export csv --ratings tiobe,pypl,redmonk,stackoverflow-survey --since 2016 --output history.csv
```

## Development checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
