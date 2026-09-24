# Subtask 06.0/06 - Coverage gate in CI & docs

**Task:** [06.0 - Test Coverage Baseline](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md) ·
**Role:** Python Expert · **Depends on:** 02, 03, 04, 05 · **Status:** ⬜ Not started

## Goal

Once total coverage is ≥ 85%, make CI enforce the same gate as the local Stop hook, and
document it.

## Baseline

- `.github/workflows/ci.yml` runs `uv run pytest` without `--cov`.
- `.claude/hooks/run_tests.py` runs `uv run pytest -q --cov=langrank --cov-report=term-missing`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `.github/workflows/ci.yml` | pytest step → `uv run pytest -q --cov --cov-report=term-missing` |
| Modify | `docs/test/code_test_coverage.md` | State the 85% floor, the xfail(strict) convention for pinned defects, and where the gate runs |
| Modify | `CLAUDE.md` | "Commands" section mentions the coverage gate |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| CI `pytest` step | workflow step | `uv run pytest -q --cov --cov-report=term-missing` | - | Uses `.coveragerc` `fail_under = 85` |

## Behaviour & validators

1. CI fails when coverage < 85% (via `.coveragerc fail_under`).
2. The hook and CI use the same `.coveragerc`.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (CI run)      | `.github/workflows/ci.yml` | E2E | green on 3.12 and 3.13 with the gate on |

## Success criteria

- [ ] `grep -n "\-\-cov" .github/workflows/ci.yml` matches.
- [ ] CI green on Python 3.12 and 3.13.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Do not lower `fail_under` to make CI pass.

## Out of scope

- Per-module coverage floors.
