# Task 04.0 - Alias Management Commands

**Milestone:** [0005 - CLI & Storage Enhancements](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) ·
**Spec source:** [plan.md § Task 04.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-040---alias-management-commands) ·
**Category:** cli · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                    | Role           | Depends on | Status         |
|----|--------------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Single-path alias match in `Database`](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/01-alias-match-repository.md)          | Python Expert  | -          | ⬜ Not started |
| 02 | [`LanguageService.resolve` with normalizer cross-check](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/02-language-resolve-service.md) | Python Expert  | 01         | ⬜ Not started |
| 03 | [`langrank languages resolve` command](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/03-languages-resolve-command.md)           | Python Expert  | 02         | ⬜ Not started |
| 04 | [Richer `languages aliases` output](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/04-languages-aliases-output.md)              | Python Expert  | -          | ⬜ Not started |
| 05 | [Resolution parity test suite](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/05-resolution-parity-tests.md)                    | Testing Expert | 02         | ⬜ Not started |
| 06 | [ADR: user-defined aliases (`alias add`) - deferred](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/06-alias-add-adr.md)        | Architect      | -          | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Make the existing alias system inspectable from the CLI: `languages resolve <name>` shows exactly
how an input string maps to a canonical language - through the same code path ingestion and query
use - and flags any disagreement between the in-code `LanguageNormalizer` and the DB alias table.

## Baseline (what already exists)

- `langrank languages aliases [--rating X]` **already exists** (`cli.py:languages_aliases`) and
  prints rating/alias/canonical from `Database.list_aliases`.
- `langrank languages show <name>` exists (resolves via `Database.alias_to_language`).
- Two resolution paths with duplicated key normalisation:
  - `normalization/languages.py:LanguageNormalizer.resolve` / `_normalize_key` (used by providers
    in `normalize()`).
  - `db/repository.py:Database.alias_to_language` / `_normalize_alias` (used by CLI queries),
    seeded from the normalizer by `seed_languages`.
  The two normalisation functions are character-identical today, but nothing enforces it.
- All seeded aliases are global (`rating_id = ""`); schema already has `valid_from`, `valid_to`,
  `notes` and a rating-specific precedence rule (`ORDER BY CASE WHEN rating_id = '' …`).
- `cli.py:_language_ids` contains a PYPL-specific `c-cpp` hint.

## Design notes

- **Read-only window, no new resolution path.** `resolve` calls a `Database` method that
  `alias_to_language` itself is refactored to use, so the command cannot drift from real
  behaviour (plan success criterion).
- **Cross-check, don't reconcile.** The command reports normalizer vs DB disagreement as a warning
  and non-zero exit option (`--strict`); it never "fixes" either side.
- **`alias add` is deferred to an ADR** (subtask 06). User aliases can change historical semantics;
  the ADR fixes how source-defined and user aliases stay distinguishable before any code exists.
- Validity ranges (`valid_from`/`valid_to`) are displayed but not yet applied to resolution; date-
  aware resolution is [Milestone 0003 Task 02.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-020---language-births-renames--alias-validity-ranges).

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `languages resolve <alias>` reproduces exactly what `Database.alias_to_language` /
      `_normalize_alias` do internally (parity suite green).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [plan.md § Read-only alias inspection](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#read-only-alias-inspection)
- [docs/adr/README.md](/docs/adr/README.md)
