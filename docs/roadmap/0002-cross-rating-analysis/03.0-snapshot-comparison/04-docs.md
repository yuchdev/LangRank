# Subtask 03.0/04 - Snapshot Docs

**Task:** [03.0 - Snapshot Comparison](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/README.md) ·
**Role:** Docs Writer · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Document the snapshot selection rules so users know exactly which publication each column
comes from and why a cell can be blank.

## Baseline

- `docs/cross-rating-analysis.md` (created by
  [01.0/06](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/06-docs.md)).
  If 01.0/06 has not landed, create the file with only this section and let 01.0/06 add its own.

## Files

| Action | Path                              | Purpose                                  |
|--------|-----------------------------------|------------------------------------------|
| Modify | `docs/cross-rating-analysis.md`   | `## Snapshots` section                   |
| Modify | `README.md`                       | Example `langrank snapshot 2020`         |

## Symbols / fields

| Symbol (doc section)                     | Kind    | Notes |
|------------------------------------------|---------|-------|
| `## Snapshots`                           | heading | |
| `### Selection rules`                    | heading | Year vs latest, one reference period per column, no borrowing |
| `### Reading dates and blanks`           | heading | `date_note` cases, `—`/`null`/`""` in each format, `*` derived marker |

## Behaviour & validators

1. Worked example uses RedMonk (semi-annual) showing a June reference with its note.
2. Options match `langrank snapshot --help` exactly.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (link check)  | `scripts/check_doc_links.py` | - | No dangling links/anchors |

## Success criteria

- [ ] Section present; `python3 scripts/check_doc_links.py docs/` reports no new problems.

## Constraints

- Absolute-from-repo-root links.

## Out of scope

- Composite docs ([02.0/05](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/05-docs.md)).
