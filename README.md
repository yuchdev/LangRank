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

## Demo

The bundled `demo` provider uses deterministic synthetic data so the full application works without network access.

```bash
uv run langrank fetch demo
uv run langrank query --rating demo --language python --years 10
uv run langrank plot --rating demo --languages python,c++,rust --years 10
uv run langrank export csv --rating demo --output demo.csv
```

## Development checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
