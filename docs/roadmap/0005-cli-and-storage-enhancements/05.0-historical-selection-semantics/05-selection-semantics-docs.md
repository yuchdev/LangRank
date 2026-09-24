# Subtask 05.0/05 - Document selection semantics

**Task:** [05.0 - Historical Selection Semantics](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md) ·
**Role:** Docs Writer · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Document the `--years`/`--until`/`--since`/`--year`/`--endpoint` rules once, with worked examples,
and flag the behaviour change for monthly sources.

## Baseline

- README usage examples use `--years 10` without defining it.

## Files

| Action | Path                  | Purpose |
|--------|-----------------------|---------|
| Modify | `README.md`           | "Time selection" section with rule + examples |
| Modify | `docs/architecture.md` | Note that `services/selection.py:resolve_window` is the single window resolver |
| Modify | `CHANGELOG.md` (create if absent) | Behaviour-change entry |

## Symbols / fields

| Symbol                 | Kind    | Notes |
|------------------------|---------|-------|
| `## Time selection`    | README heading | Rule, policy table, 3 worked examples (annual stale source, monthly, `--until`) |

## Behaviour & validators

1. The README rule text matches `YEARS_HELP` in `cli.py` word-for-word.
2. Worked examples match the regression tests in subtask 04.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (link check)  | `scripts/check_doc_links.py docs/` | - | No new dangling links |

## Success criteria

- [ ] Section exists; examples consistent with tests.

## Constraints

- Absolute-from-repo-root links.

## Out of scope

- Milestone 0002 snapshot semantics.
