# Subtask 01.0/06 - Capabilities ↔ Metadata Contract Test

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
**Role:** Testing Expert · **Depends on:** 03, 04 · **Status:** ⬜ Not started

## Goal

A single parametrized contract test, run over **every registered provider**, proves each
provider's declared capabilities agree with its metadata and behaviour. The same test is
reused unchanged by [Task 02.0](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md)
to vet plugin providers.

## Baseline

- `tests/contract/test_production_providers.py` parametrizes provider classes by hand;
  `tests/contract/test_demo_provider.py` covers demo.
- Fixtures: `tests/fixtures/{tiobe,pypl,redmonk,stackoverflow-survey}/sample.csv`.

## Files

| Action | Path                                            | Purpose                                     |
|--------|-------------------------------------------------|---------------------------------------------|
| Create | `tests/contract/test_provider_capabilities_contract.py` | The contract suite                  |
| Create | `tests/contract/_provider_contract.py`          | Reusable `assert_provider_contract(provider, fixture_bytes)` helper (imported by Task 02.0 tests) |

## Symbols / fields

| Symbol                        | Kind     | Type / signature                                                        | Default | Notes |
|-------------------------------|----------|-------------------------------------------------------------------------|---------|-------|
| `assert_provider_contract`    | function | `(provider: RatingProvider, fixture: bytes \| None) -> None`             | -       | Raises `AssertionError` with a readable message per rule |
| `PROVIDER_FIXTURES`           | constant | `dict[str, str]`                                                        | -       | provider ID → fixture path; demo uses `None` (self-generating) |

## Behaviour & validators

The helper asserts, for each provider:

1. `capabilities().native_granularity == metadata().native_granularity`.
2. `(supports_rank, supports_value) == derive_value_capabilities(metadata())`.
3. Every `RANK`-kind metric has `higher_is_better is False` and `unit == "rank"`.
4. `metadata().default_metric` is one of `metadata().metrics` IDs.
5. `supports_status_check` ⇔ `upstream_latest_period() is not None`.
6. If a fixture is given: `parse → normalize → validate` yields `report.ok`, and every observed
   `metric_id` is a declared metric; if `supports_rank`, at least one observation has a
   RANK-kind metric with non-`None` `rank`.
7. If `supports_raw_cache`: `fetch(FetchRequest())` with a tmp cache dir returns a payload
   whose `artifact` is not `None` (built-ins read bundled CSVs, so no network); with
   `no_cache=True` the artifact is `None`.
8. The test enumerates `ProviderRegistry(tmp_path).all()` - adding a provider without
   updating `PROVIDER_FIXTURES` fails with a message naming the missing ID.

## Tests

| Test function                                    | File                                                   | Type     | Asserts |
|--------------------------------------------------|--------------------------------------------------------|----------|---------|
| `test_registered_provider_contract`              | `tests/contract/test_provider_capabilities_contract.py` | Contract (Integration) | Rules 1-7 per provider, parametrized by ID |
| `test_every_registered_provider_has_fixture`     | `tests/contract/test_provider_capabilities_contract.py` | Unit     | Rule 8 |
| `test_contract_helper_rejects_inconsistent_stub` | `tests/contract/test_provider_capabilities_contract.py` | Mock     | Stub with `supports_rank=True` but no RANK metric → `AssertionError` |

## Success criteria

- [ ] Suite passes for all five built-ins; the negative stub test proves the helper actually checks.
- [ ] Runs under `pytest -m "not integration"` (no network).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Fixture-driven only ([CLAUDE.md](/CLAUDE.md) § Conventions: contract tests are fixture-driven).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Running the contract against plugins - [02.0/04](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/04-fixture-plugin-package.md).
