# Subtask 04.0/05 - Scaffold Tests

**Task:** [04.0 - Provider Intake Scaffold](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/README.md) ·
**Role:** Testing Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Pin the scaffold's gate, idempotence, never-overwrite behavior, and generated-code
quality with tests.

## Baseline

- `tests/scripts/conftest.py` loads `scripts/*.py` modules (from Task 01.0/02).
- The valid/invalid note fixtures come from Task 01.0/02.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `tests/scripts/test_scaffold_provider.py`    | Tests |
| Create | `tests/fixtures/source-notes/scaffold/*.md`  | `planned` note that passes the gate; `candidate` note; `planned` note with `automation: unknown` |

## Symbols / fields

| Symbol           | Kind    | Notes |
|------------------|---------|-------|
| `fake_repo`      | fixture | Copies `docs/roadmap/_templates/`, a minimal `docs/roadmap/0001-x/plan.md` with a `## Tasks` table, and the fixture notes into `tmp_path` |

## Behaviour & validators

1. Tests run the script's functions against `fake_repo` and never write into the real repo.

## Tests

| Test function                                  | File                                      | Type        | Asserts |
|------------------------------------------------|-------------------------------------------|-------------|---------|
| `test_gate_rejects_candidate_status`           | `tests/scripts/test_scaffold_provider.py` | Unit        | `GateError` |
| `test_gate_rejects_unknown_automation`         | same                                      | Unit        | `GateError` |
| `test_plan_lists_expected_paths`               | same                                      | Unit        | Provider, contract test, `.gitkeep` |
| `test_dry_run_writes_nothing`                  | same                                      | Unit        | Tree unchanged; exit 0 |
| `test_second_run_skips_everything`             | same                                      | Unit        | All `skip`; file hashes unchanged |
| `test_existing_file_is_never_overwritten`      | same                                      | Unit        | Pre-created provider file keeps its content |
| `test_generated_provider_passes_ruff_and_mypy` | same                                      | Integration | `subprocess` `ruff check` + `mypy` on the rendered file (skip if the tools are unavailable) |
| `test_generated_contract_test_is_skipped`      | same                                      | Integration | `pytest --collect-only` + run → 1 skipped |
| `test_roadmap_stub_has_eight_subtasks`         | same                                      | Unit        | README + `01-…08-` files |
| `test_roadmap_stub_links_resolve`              | same                                      | Integration | `check_doc_links` on the generated folder → 0 problems |
| `test_next_task_number`                        | same                                      | Unit        | `## Tasks` with `01.0`, `02.0` → `"03.0"` |

## Success criteria

- [ ] All tests pass.
- [ ] Run `/document-tests tests/scripts/test_scaffold_provider.py`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No network access. Everything runs inside `tmp_path`.

## Out of scope

- Skill acceptance (subtask 04).
