# Subtask 02.0/04 - Out-of-Tree Fixture Plugin Package

**Task:** [02.0 - External Provider Plugin Loading](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md) ·
**Role:** Testing Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Prove the plan's success criterion end to end: a real, separately packaged provider -
living outside `src/langrank/` and importing only `langrank.providers.api` - is discovered
through genuine `importlib.metadata` machinery (not a monkeypatched `entry_points`), passes the
Task 01.0 provider contract, and round-trips through `fetch → query`.

## Baseline

- Monkeypatched discovery tests from subtasks 02-03.
- Contract helper `tests/contract/_provider_contract.py:assert_provider_contract` from
  [01.0/06](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/06-capabilities-contract-test.md).

## Files

| Action | Path                                                                   | Purpose |
|--------|------------------------------------------------------------------------|---------|
| Create | `tests/fixtures/plugins/langrank_example_plugin/pyproject.toml`        | Declares `[project.entry-points."langrank.providers"] example-plugin = "langrank_example_plugin:make_provider"` |
| Create | `tests/fixtures/plugins/langrank_example_plugin/src/langrank_example_plugin/__init__.py` | Offline provider (bundled tiny CSV), `LANGRANK_PLUGIN_API = (1, 0)` |
| Create | `tests/fixtures/plugins/langrank_example_plugin/src/langrank_example_plugin/data.csv` | 2 languages × 3 years, `rank` + `score` metrics |
| Create | `tests/contract/test_plugin_package.py`                                | Tests below |
| Create | `tests/fixtures/plugins/conftest_helpers.py` *(or fixture in `tests/conftest.py`)* | `installed_plugin` fixture |

## Symbols / fields

| Symbol                  | Kind     | Type / signature                                     | Default | Notes |
|-------------------------|----------|------------------------------------------------------|---------|-------|
| `make_provider`         | function | `(cache_dir: Path) -> ExamplePluginProvider`         | -       | In fixture package |
| `ExamplePluginProvider.provider_id` | attr | `str`                                        | `"example-plugin"` | |
| `installed_plugin`      | pytest fixture | `-> Iterator[None]`                            | -       | Writes a `langrank_example_plugin-0.0.1.dist-info/` with `METADATA` + `entry_points.txt` into `tmp_path`, prepends `tmp_path` and the package `src/` to `sys.path`, invalidates `importlib` caches, restores on teardown |

## Behaviour & validators

1. The fixture package imports **only** from `langrank.providers.api` (grep-checked by a test).
2. The provider is fully offline and deterministic (same rules as `providers/demo.py`).
3. Its language names map to existing canonical languages (e.g. `Python`, `Rust`), per ADR
   decision 4 (no plugin-contributed languages in API v1).
4. The dist-info approach exercises real `importlib.metadata.entry_points()`; no pip install at
   test time, no network, no mutation of the dev venv.

## Tests

| Test function                                   | File                                   | Type        | Asserts |
|-------------------------------------------------|----------------------------------------|-------------|---------|
| `test_fixture_plugin_is_discovered`             | `tests/contract/test_plugin_package.py` | Integration | With `installed_plugin`, `ProviderRegistry(tmp).get("example-plugin")` works and `plugin_result.loaded[0].distribution == "langrank_example_plugin"` |
| `test_fixture_plugin_passes_provider_contract`  | `tests/contract/test_plugin_package.py` | Contract    | `assert_provider_contract(provider, None)` |
| `test_fixture_plugin_fetch_and_query_round_trip`| `tests/contract/test_plugin_package.py` | E2E         | `CliRunner`: `fetch example-plugin` then `query --rating example-plugin --language python` returns rows |
| `test_fixture_plugin_imports_only_public_api`   | `tests/contract/test_plugin_package.py` | Unit        | AST scan: every `from langrank...` import is `langrank.providers.api` |
| `test_fixture_plugin_absent_without_install`    | `tests/contract/test_plugin_package.py` | Integration | Without the fixture, ID unknown → `ProviderError` |

## Success criteria

- [ ] Plan success criterion demonstrated: registration with **no change to `langrank` core** (the fixture lives entirely under `tests/fixtures/plugins/`).
- [ ] Tests are offline and fast (<1 s total), so they are **not** marked `integration` and run in
      the default suite, including `pytest -m "not integration"`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `mypy src` scope unchanged (fixture package is under `tests/`); ruff still lints it.
- No test writes outside `tmp_path`.

## Out of scope

- Publishing a template/cookiecutter plugin repo (mention in the author guide as future work).
