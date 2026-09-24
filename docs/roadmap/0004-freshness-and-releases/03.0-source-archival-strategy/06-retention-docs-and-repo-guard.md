# Subtask 03.0/06 - Retention Docs & Repo Size Guard

**Task:** [03.0 - Source Archival Strategy](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md) ·
**Role:** Docs Writer (+ Testing Expert for the guard test) · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Document retention policies and precedence, and add an automated guard that stops large
raw/copyrighted datasets from being committed into the repository.

## Baseline

- Bundled snapshots live in `src/langrank/providers/data/*.csv`; fixtures in
  `tests/fixtures/<provider>/`. No size guard exists.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `docs/ops/raw-artifact-retention.md` | Policies, precedence table, examples, provenance guarantee |
| Modify | `README.md` | Config section: `retention`, `LANGRANK_RETENTION`, `--retention` |
| Modify | `docs/README.md` | Register doc |
| Create | `tests/unit/test_repo_data_size.py` | Size guard |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `MAX_TRACKED_DATA_BYTES` | constant (test) | `int` | `1_048_576` | Per file |
| `DATA_GLOBS` | constant (test) | `tuple[str, ...]` | `("src/langrank/providers/data/*", "tests/fixtures/**/*")` | |

## Behaviour & validators

1. Guard fails with the offending path(s) when any matched file exceeds the limit;
   the failure message points to the [0001 legal gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).
2. Doc includes the full precedence chain from the task README and a TOML example with
   `[langrank.retention] stackoverflow-survey = "yearly"`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_no_large_data_files_in_repo` | `tests/unit/test_repo_data_size.py` | Unit | every matched file ≤ limit |

## Success criteria

- [ ] `python3 scripts/check_doc_links.py docs/` reports no new problems.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Absolute-from-root links per [docs/roadmap/README.md](/docs/roadmap/README.md).

## Out of scope

- Git LFS or external artifact hosting.
