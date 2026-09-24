# Subtask 03.0/07 - Document the quality checks

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Docs Writer · **Depends on:** 06 · **Status:** ⬜ Not started

## Goal

A reference page listing every quality check (code, severity, what it means, typical
legitimate causes, how to investigate), plus README usage.

## Baseline

- No quality docs exist; `README.md` documents `validate`.

## Files

| Action | Path                      | Purpose |
|--------|---------------------------|---------|
| Create | `docs/data-quality.md`    | Check reference + JSON schema |
| Modify | `README.md`               | `langrank quality` usage + difference from `validate` |
| Modify | `docs/README.md`          | Registry entry |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| One `### <code>` heading per check | heading | in `docs/data-quality.md` | - | anchors usable from finding messages |

## Behaviour & validators

1. Every code in `CHECKS` has a heading (checked by a test).
2. States explicitly: the command flags; it never edits or deletes data.

## Tests

| Test function                           | File                                    | Type | Asserts |
|-----------------------------------------|-----------------------------------------|------|---------|
| `test_every_check_documented`           | `tests/unit/test_quality_docs.py`       | Unit | each `CHECKS` key appears as `### <code>` in `docs/data-quality.md` |

## Success criteria

- [ ] Doc exists; test passes; link check clean.

## Constraints

- Absolute links.

## Out of scope

- Tutorials.
