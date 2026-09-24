# Subtask 06.0/01 - Coverage configuration fix

**Task:** [06.0 - Test Coverage Baseline](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Make `.coveragerc` describe this project, so `uv run pytest --cov` measures `src/langrank`
with no extra flags, and plots never open a window during tests.

## Baseline

- `.coveragerc` `[run] source = src/aegis_swr` (template leftover); `fail_under = 85`, `branch = True`.
- `tests/conftest.py` has no matplotlib backend fixture.

## Files

| Action | Path                  | Purpose                                              |
|--------|-----------------------|------------------------------------------------------|
| Modify | `.coveragerc`         | `source = langrank`; keep `branch`, `fail_under = 85` |
| Modify | `tests/conftest.py`   | session-scoped autouse fixture forcing `Agg` backend |

## Symbols / fields

| Symbol                         | Kind            | Type / signature   | Default | Notes |
|--------------------------------|-----------------|--------------------|---------|-------|
| `[run] source`                 | config          | str                | `langrank` | package name, not path |
| `_matplotlib_agg_backend`      | pytest fixture  | `() -> None`       | -       | `autouse=True, scope="session"`; `matplotlib.use("Agg")` |

## Behaviour & validators

1. `uv run pytest --cov` (no `=langrank`) reports `src/langrank/*` modules.
2. No test run opens a GUI window.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (none new)    | -    | -    | Verified by the coverage report listing `src/langrank/cli.py` |

## Success criteria

- [ ] `grep -n "aegis_swr" .coveragerc` returns nothing.
- [ ] `uv run pytest --cov` lists `src/langrank` modules.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Do not lower `fail_under`.

## Out of scope

- Adding the gate to CI - [subtask 06](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/06-coverage-gate-ci.md).
