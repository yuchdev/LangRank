# Test conventions

This document describes project-wide test conventions, markers, and helpers that every contributor
should know before writing or reviewing tests. CI runs `uv run pytest` with no extra flags; all
conventions here are compatible with that invocation.

## Test layout

```
tests/
  unit/           # Fast, no-network: models, config, individual provider methods
  integration/    # Full-pipeline tests (DemoProvider + real Database); no network by default
  contract/       # Provider contract/golden tests (fixture-driven, no network)
  fixtures/       # Static fixture files consumed by tests
  conftest.py     # Shared fixtures, marker hooks
```

## Pytest markers

Markers are declared in `pyproject.toml` under `[tool.pytest.ini_options] markers`.

### `integration`

Applied to tests that exercise a multi-stage pipeline path (e.g. fetch -> database -> query). These
tests still run offline (using `DemoProvider` or pre-seeded fixtures); they are separated from
`unit/` to reflect a wider test scope, not a network dependency.

```python
import pytest
pytestmark = pytest.mark.integration
```

Run integration tests only:

```bash
uv run pytest -m integration
```

Skip integration tests (unit tests only):

```bash
uv run pytest -m "not integration"
```

### `live`

Applied to tests that perform **real outbound network requests**. These tests are **skipped by
default** in all plain `uv run pytest` runs (including CI). They execute only when the opt-in
environment variable is set:

```bash
LANGRANK_LIVE_TESTS=1 uv run pytest -m live
```

The skip logic lives in `tests/conftest.py::pytest_collection_modifyitems`. Any test that issues a
real HTTP request must carry the `live` marker; tests without it must not perform network calls.

```python
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.live]
```

## Contract tests and golden files

Provider contract tests live in `tests/contract/`. Each provider's contract suite:

1. Loads a static fixture from `tests/fixtures/<provider-id>/`.
2. Drives the real `parse()` -> `normalize()` pipeline (no network, no database).
3. Compares the resulting `Observation` list against a checked-in JSON golden file using
   `tests/contract/_golden.py::assert_matches_golden`.

### Golden file format

Golden files are stored as a JSON array of `Observation.to_dict()` dicts, sorted by
`(metric_id, language_id, period_start)` for stable diffs. The non-deterministic `retrieved_at`
field is excluded from comparison.

### Regenerating golden files

When an intentional normalization change changes the expected output, regenerate with:

```bash
LANGRANK_UPDATE_GOLDEN=1 uv run pytest tests/contract/
```

Review the resulting diff carefully before committing. Never set `LANGRANK_UPDATE_GOLDEN=1` to
silence an unexpected diff - a changed golden is a changed observation, which is the class of
silent data-bug these tests exist to catch.

### Adding a new provider's contract test

1. Create `tests/fixtures/<provider-id>/` and add at minimum one fixture file.
2. Create `tests/contract/test_<provider_id>_provider.py` importing `assert_matches_golden` from
   `_golden`.
3. Run with `LANGRANK_UPDATE_GOLDEN=1` once to create the initial golden file.
4. Commit both the fixture and the golden file; subsequent runs validate against them.

## Running the full test suite

```bash
uv run pytest                          # all tests (live tests skipped)
uv run pytest -m "not integration"     # unit tests only
LANGRANK_LIVE_TESTS=1 uv run pytest -m live   # live network tests (requires connectivity)
LANGRANK_UPDATE_GOLDEN=1 uv run pytest tests/contract/   # regenerate all golden files
```
