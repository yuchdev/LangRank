# Subtask 04.0/02 - Scaffold Script

**Task:** [04.0 - Provider Intake Scaffold](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Add `scripts/scaffold_provider.py`. It loads and gates a source note, then renders the
provider files idempotently, with `--dry-run` support.

## Baseline

- `scripts/check_source_notes.py:load_notes()` / `SourceNote` (Task 01.0/02). Import it with
  `importlib` from the same directory, the way the tests do.
- The templates come from subtask 01.

## Files

| Action | Path                             | Purpose |
|--------|----------------------------------|---------|
| Create | `scripts/scaffold_provider.py`   | CLI + planning + rendering |

## Symbols / fields

| Symbol              | Kind      | Type / signature                                                                   | Default | Notes |
|---------------------|-----------|------------------------------------------------------------------------------------|---------|-------|
| `PlannedFile`       | dataclass | frozen; `path: Path`, `content: str`, `action: Literal["create", "skip"]`         | - | `skip` when the path exists |
| `GateError`         | class     | `Exception`                                                                        | - | |
| `check_gate()`      | function  | `(note: SourceNote) -> None`                                                       | - | Raises `GateError` |
| `plan_provider()`   | function  | `(note: SourceNote, *, repo_root: Path) -> list[PlannedFile]`                      | - | Pure apart from `Path.exists` |
| `apply_plan()`      | function  | `(plan: Sequence[PlannedFile]) -> None`                                            | - | Writes only `create` entries; `open(..., "x")` |
| `main()`            | function  | `(argv: list[str] \| None = None) -> int`                                          | - | Args: `source_id`, `--milestone NNNN`, `--task TT.t`, `--dry-run`, `--repo-root` |

## Behaviour & validators

1. The generated files are:
   - `src/langrank/providers/<module>.py`
   - `tests/contract/test_<module>_provider.py`
   - `tests/fixtures/<provider_id>/.gitkeep`
   - the roadmap stub from subtask 03, when `--milestone` is given
2. Gate failures return exit 2 with the reason. The gate fails when:
   - the note is not found;
   - the note has validation problems;
   - `status` is not `planned`;
   - `terms_url` is null;
   - `automation` is `unknown` or `forbidden`.

   With `forbidden`, the message says that the source can only be supported as a manual
   `langrank import`, if at all.
3. Files are opened with mode `"x"` (exclusive create). An existing file is never truncated,
   even under a race.
4. Output is one line per planned file, `CREATE <path>` or `SKIP   <path> (exists)`,
   followed by the rendered registry/alias hint.
5. With `--dry-run`, it prints the same lines prefixed `[dry-run]` and writes nothing.
6. Exit 0 on success, including the case where every file is skipped.

## Tests

Covered in [subtask 05](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/05-scaffold-tests.md).

## Success criteria

- [ ] `python scripts/scaffold_provider.py --help` lists all arguments.
- [ ] The script is stdlib-only.

## Constraints

- It never modifies `providers/registry.py`, `normalization/languages.py` or any existing
  file.

## Out of scope

- Roadmap stub content: [subtask 03](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/03-roadmap-task-stub-generation.md).
