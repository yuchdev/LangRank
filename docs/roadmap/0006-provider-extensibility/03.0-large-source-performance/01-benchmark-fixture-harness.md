# Subtask 03.0/01 - Benchmark Fixture Generator & Harness

**Task:** [03.0 - Large-Source Performance Hardening](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/README.md) ·
**Role:** Testing Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

A deterministic generator for large synthetic source files and a benchmark harness that
records wall time and peak memory of `fetch → parse → normalize → validate → upsert`, excluded
from the default test run. Establishes the baseline numbers the other subtasks improve on.

## Baseline

- `pyproject.toml` `[tool.pytest.ini_options]`: `addopts = "-q"`, marker `integration` only.
- Largest real source shape: SO Developer Survey public CSV (tens of thousands of respondents,
  semicolon-separated multi-select language column).

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `scripts/generate_benchmark_fixture.py`      | CLI: `--shape {survey,monthly} --rows N --seed S --output PATH` |
| Create | `tests/benchmarks/__init__.py`               | Package marker |
| Create | `tests/benchmarks/conftest.py`               | `large_survey_csv`, `large_monthly_csv` session fixtures (generated into `tmp_path_factory`, never committed) |
| Create | `tests/benchmarks/test_pipeline_benchmark.py`| Harness tests |
| Modify | `pyproject.toml`                             | Register `benchmark` marker; `addopts = "-q -m 'not benchmark'"` |
| Create | `docs/dev/performance.md`                    | How to run; baseline results table (filled by this subtask) |

## Symbols / fields

| Symbol                        | Kind     | Type / signature                                                   | Default | Notes |
|-------------------------------|----------|--------------------------------------------------------------------|---------|-------|
| `generate_survey_csv`         | function | `(rows: int, seed: int, output: Path) -> Path`                     | -       | SO-survey-like: `ResponseId`, `LanguageHaveWorkedWith` (`;`-joined), filler columns to ~80 |
| `generate_monthly_csv`        | function | `(languages: int, months: int, seed: int, output: Path) -> Path`   | -       | TIOBE-like `period,language,rank,rating,source_url` |
| `BenchmarkResult`             | dataclass | frozen: `stage: str`, `seconds: float`, `peak_mib: float`, `rows: int` | - | In `tests/benchmarks/conftest.py` |
| `measure`                     | context manager | `(stage: str, rows: int) -> Iterator[BenchmarkResult-builder]` | - | `time.perf_counter` + `tracemalloc` peak |

## Behaviour & validators

1. Generator is deterministic: same args → byte-identical file (seeded `random.Random`).
2. Language names used are ones `LanguageNormalizer` resolves (no `UnknownLanguageError` noise).
3. Default sizes: survey 90 000 rows; monthly 50 languages × 240 months × 2 metrics ≈ 24 000
   observations, plus a `--scale` multiplier to reach 200 000 observations.
4. Benchmarks feed files through the **real** providers via `FetchPayload(artifact=None, content=...)`
   (and via `content_path` once subtask 03 lands) and a real tmp `Database`.
5. Results appended to `benchmark-results.json` in `tmp_path` and printed; no hard assertions in
   this subtask (budget assertions arrive in subtask 05).

## Tests

| Test function                                | File                                          | Type        | Asserts |
|----------------------------------------------|-----------------------------------------------|-------------|---------|
| `test_generator_is_deterministic`            | `tests/unit/test_benchmark_generator.py`      | Unit        | Two runs, same seed → same sha256 (small N, runs in default suite) |
| `test_benchmark_survey_pipeline`             | `tests/benchmarks/test_pipeline_benchmark.py` | Integration (`@pytest.mark.benchmark`) | Runs all stages, records result |
| `test_benchmark_monthly_pipeline`            | `tests/benchmarks/test_pipeline_benchmark.py` | Integration (`@pytest.mark.benchmark`) | Same |
| `test_benchmark_reupsert_unchanged`          | `tests/benchmarks/test_pipeline_benchmark.py` | Integration (`@pytest.mark.benchmark`) | Second upsert of identical data: inserted=0, updated=0 |

## Success criteria

- [ ] `uv run pytest` collects zero `benchmark` tests; `uv run pytest -m benchmark` runs them.
- [ ] `docs/dev/performance.md` records baseline seconds/MiB per stage for both shapes.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Generated fixtures are never committed (size, and survey data licensing - synthetic only).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Optimisations (subtasks 02-04); CI gating (subtask 05).
