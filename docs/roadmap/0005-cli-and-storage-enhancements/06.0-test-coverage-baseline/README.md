# Task 06.0 - Test Coverage Baseline

**Milestone:** [0005 - CLI & Storage Enhancements](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) ·
**Spec source:** [plan.md § Task 06.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-060---test-coverage-baseline) ·
**Category:** quality · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                              | Role           | Depends on | Status         |
|----|--------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Coverage configuration fix](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/01-coverage-config.md)       | Python Expert  | -          | ⬜ Not started |
| 02 | [HTTP client tests](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/02-http-client-tests.md)              | Testing Expert | 01         | ⬜ Not started |
| 03 | [Status service & registry tests](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/03-status-registry-tests.md) | Testing Expert | 01         | ⬜ Not started |
| 04 | [CLI command tests](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/04-cli-command-tests.md)              | Testing Expert | 01         | ⬜ Not started |
| 05 | [Repository read-path & JSON export tests](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/05-repository-export-tests.md) | Testing Expert | 01 | ⬜ Not started |
| 06 | [Coverage gate in CI & docs](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/06-coverage-gate-ci.md)      | Python Expert  | 02-05      | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Bring the existing code base to the 85% line+branch coverage floor that `.coveragerc`
(`fail_under = 85`) and the `run_tests` Stop hook already enforce, **before** the feature
milestones add more code. Only characterization tests are written: they pin current behaviour,
and where the current behaviour is a known defect they pin it with `pytest.mark.xfail(strict=True)`
and link the owning roadmap subtask rather than fixing it here.

## Baseline (what already exists)

Measured 2026-09-24 with `uv run pytest -q --cov=langrank --cov-report=term-missing`
(19 tests): **73.27% total**. The biggest gaps:

| Module                              | Cover  | Uncovered surface                                               |
|-------------------------------------|--------|-----------------------------------------------------------------|
| `src/langrank/util/http.py`         | 0%     | `HttpClientFactory.build/get_bytes/map_error` - unused by providers today |
| `src/langrank/cli.py`               | 43.8%  | `ratings`, `languages`, `import`, `export csv/json`, `plot`, `validate`, `coverage`, `status`, `main()` |
| `src/langrank/services/status.py`   | 44.7%  | `StatusService.statuses` state derivation (`current`/`stale`/`ready`/`unknown`) |
| `src/langrank/exports/json_export.py` | 67.9% | `export_json_records`, `_json_default`, `write_metadata_sidecar` |
| `src/langrank/db/repository.py`     | 77.0%  | `list_metrics`, `list_methodology_notes`, `list_aliases`, `language_suggestions`, `coverage`, fetch-run lookups |

- `.coveragerc` still carries a template value `source = src/aegis_swr`; it only works because
  the hook passes `--cov=langrank` explicitly.
- CI (`.github/workflows/ci.yml`) runs plain `uv run pytest` with no coverage gate, so the
  hook and CI disagree.

## Design notes

- **Characterize, don't refactor.** No `src/` change except the configuration in subtask 01.
  Bugs found while writing tests go to the [roadmap defect ledger](/docs/roadmap/README.md#cross-milestone-defect-ledger).
- **Known defects pinned as strict xfail**, e.g. `plot --metric tiobe-rank` not inverting the
  axis ([0006 Task 01.0 subtask 02](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/02-metric-role-lookups.md)).
  A strict xfail turns into a failure the moment the fix lands, which forces the xfail marker to be
  removed and the test to become a regression test.
- **Plots** use the matplotlib `Agg` backend (`MPLBACKEND=Agg` via a `conftest.py` fixture);
  `plot` without `--output` calls `plt.show()`, which tests must never reach.
- **Network** is never touched: `httpx.MockTransport` for `HttpClientFactory`.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `uv run pytest -q --cov=langrank` reports ≥ 85% total and exits 0 under `fail_under = 85`.
- [ ] CI enforces the same gate as the Stop hook.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/test/code_test_coverage.md](/docs/test/code_test_coverage.md) - coverage conventions.
- `.claude/hooks/run_tests.py` - the Stop hook that runs `pytest --cov`.
