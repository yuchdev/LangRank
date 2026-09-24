# Subtask 01.0/08 - Scheduled-Update Docs & Example Workflow

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Docs Writer · **Depends on:** 07 · **Status:** ⬜ Not started

## Goal

Document freshness, `status --json`, `update`, and the scheduled-fetch policy, and provide
a copy-paste example GitHub Actions workflow and cron line - **not** an enabled workflow
in `.github/workflows/`.

## Baseline

- `.github/workflows/ci.yml` runs lint/type/test only. No ops docs directory exists.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `docs/ops/scheduled-updates.md` | How freshness works, mechanisms, `update` semantics, policy + override precedence, exit codes |
| Create | `docs/ops/examples/langrank-update.yml` | Example GH Actions workflow (`schedule` + `workflow_dispatch`, `uv run langrank update --scheduled --summary-file "$GITHUB_STEP_SUMMARY"`, DB cached via `actions/cache`) |
| Modify | `README.md` | Short "Keeping data fresh" section linking the ops doc |
| Modify | `docs/README.md` | Register new docs |
| Create | `tests/unit/test_ops_examples.py` | Parse example YAML-free check (string asserts) |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| Example workflow `on.schedule` | YAML | weekly cron `"17 4 * * 1"` | - | Off-peak, low frequency |
| Example workflow `permissions` | YAML | `contents: read` | - | Least privilege |

## Behaviour & validators

1. The example uses `--scheduled` (never manual mode) so the policy gate applies.
2. The doc states plainly that hosted automation is opt-in and must respect each source's
   terms ([milestone 0001 gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)).
3. The example lives outside `.github/workflows/` so it never runs in this repo.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_example_workflow_uses_scheduled_flag` | `tests/unit/test_ops_examples.py` | Unit | file contains `langrank update --scheduled` and `contents: read` |
| `test_example_workflow_not_enabled_in_repo` | same | Unit | no file under `.github/workflows/` invokes `langrank update` |

## Success criteria

- [ ] `python3 scripts/check_doc_links.py docs/` reports no new problems.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Absolute-from-root links (`/docs/...`) per [docs/roadmap/README.md](/docs/roadmap/README.md).
- No secrets in the example; no token needed for read-only runs.

## Out of scope

- Publishing releases from CI (Task 02.0).
