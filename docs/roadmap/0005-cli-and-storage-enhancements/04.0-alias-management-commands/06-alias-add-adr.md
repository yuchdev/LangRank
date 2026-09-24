# Subtask 04.0/06 - ADR: user-defined aliases (`alias add`) - deferred

**Task:** [04.0 - Alias Management Commands](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
**Role:** Architect · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Record, via `/adr-write`, how a future `langrank languages alias add …` would work and why it is
deferred - without writing any code - so source-defined parsing aliases can never be silently
overridden by user lookup aliases.

## Baseline

- [docs/adr/0001-config-loading-via-layered-settings.md](/docs/adr/0001-config-loading-via-layered-settings.md) is the only ADR; template at [docs/adr/template.md](/docs/adr/template.md).
- `language_aliases` has no origin column; `seed_languages` upserts from code on every
  `Database()` construction (a user row with the same `(rating_id, source_name_norm)` would be
  overwritten - one of the hazards the ADR must address).

## Files

| Action | Path                                              | Purpose |
|--------|---------------------------------------------------|---------|
| Create | `docs/adr/0002-user-defined-language-aliases.md`  | ADR, status **Proposed (deferred)** (take next free number if 0002 is used) |
| Modify | `docs/adr/README.md`                              | Index row |

## Symbols / fields

| ADR section         | Must decide |
|---------------------|-------------|
| Context             | Two alias roles: parsing (source-defined, affects stored `language_id`) vs lookup (user convenience, affects only CLI input) |
| Options             | (a) never support; (b) separate `user_language_aliases` table used only by CLI input resolution; (c) `origin` column in `language_aliases` |
| Decision            | Recommended (b): user aliases never participate in provider `normalize()`, so stored history cannot change |
| Consequences        | Precedence (source > user), conflict error on shadowing, export/release metadata listing active user aliases, `languages aliases` `Origin=user` |
| Revisit trigger     | A concrete user request plus Milestone 0003 Task 02.0 validity-range semantics landed |

## Behaviour & validators

1. The ADR states explicitly that user aliases must not rewrite existing observations.
2. The ADR links this task and [Milestone 0003 Task 02.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-020---language-births-renames--alias-validity-ranges).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (link check)  | `scripts/check_doc_links.py docs/adr` | - | No dangling links |

## Success criteria

- [ ] ADR exists with status Proposed (deferred) and the decisions above.
- [ ] No `alias add` code is written.

## Constraints

- Follow [docs/adr/README.md](/docs/adr/README.md) and the MADR template.

## Out of scope

- Implementation of `alias add`.
