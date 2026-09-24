# Subtask 01.0/01 - ADR: `methodology_notes` is the canonical break table

**Task:** [01.0 - Methodology Break Tracking](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) ·
**Role:** Architect · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Record, in an ADR, the decision to extend the existing `methodology_notes` table instead of
adding the `rating_methodologies` table proposed in plan.md, and fix the vocabulary
("segment", "break", `break_kind`) the rest of the task uses.

## Baseline

- `src/langrank/db/migrations.py` migration 2 (`methodology_notes`).
- `src/langrank/models.py:MethodologyNote`, `src/langrank/db/repository.py:Database.list_methodology_notes`.
- [docs/adr/README.md](/docs/adr/README.md) and [docs/adr/template.md](/docs/adr/template.md)
  (MADR); next free ADR number is `0002` on current master.

## Files

| Action | Path                                                     | Purpose                                   |
|--------|----------------------------------------------------------|-------------------------------------------|
| Create | `docs/adr/0002-methodology-notes-as-break-register.md`   | The ADR (use `/adr-write`)                |
| Modify | `docs/adr/README.md`                                     | Add the ADR to the index                  |
| Modify | `docs/roadmap/0003-historical-data-quality/plan.md`      | Task 01.0 bullet: point `rating_methodologies` at the ADR |

## Symbols / fields

| Symbol                 | Kind     | Type / signature | Default | Notes                                              |
|------------------------|----------|------------------|---------|----------------------------------------------------|
| ADR status             | metadata | `Accepted`       | -       | Must be Accepted before subtask 02 starts          |
| Considered options     | section  | ≥ 3 options      | -       | (a) extend `methodology_notes`, (b) new `rating_methodologies` table + view, (c) JSON in `ratings` |

## Behaviour & validators

1. The ADR defines: *segment* = one `methodology_notes` row; *break* = the `valid_from` of any
   segment whose `break_kind != 'initial'`; open-ended bound = `''` (existing convention).
2. The ADR lists the columns subtask 02 adds (`break_kind`, `affects_metrics`, `announced_at`)
   and the allowed `break_kind` values.
3. The ADR states the "record, never correct" rule and the citation rule (a break requires a
   `source_url` plus a source-note entry).
4. The ADR states that overlapping segments for the same metric are invalid (`methodology_overlap`).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (docs only) | -    | -    | `python3 scripts/check_doc_links.py docs/adr docs/roadmap/0003-historical-data-quality` reports 0 problems |

## Success criteria

- [ ] `docs/adr/0002-methodology-notes-as-break-register.md` exists with status Accepted.
- [ ] plan.md Task 01.0 no longer implies a new table; it links the ADR.
- [ ] Link check passes for the touched files.

## Constraints

- ADR follows the MADR template and linking convention in [docs/roadmap/README.md](/docs/roadmap/README.md#linking-convention).
- Does not change code.

## Out of scope

- The migration itself ([subtask 02](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/02-break-kind-migration.md)).
