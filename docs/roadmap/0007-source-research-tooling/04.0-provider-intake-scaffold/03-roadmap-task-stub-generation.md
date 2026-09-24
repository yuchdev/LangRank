# Subtask 04.0/03 - Roadmap Task Stub Generation

**Task:** [04.0 - Provider Intake Scaffold](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

When `--milestone NNNN` is given, `plan_provider()` also plans a roadmap task folder. The
folder has a README generated from `docs/roadmap/_templates/task-readme.md`, plus a standard
set of provider subtask stubs generated from `subtask.md`.

## Baseline

- Folder convention (from [docs/roadmap/README.md](/docs/roadmap/README.md)):
  `docs/roadmap/{NNNN}-{milestone-slug}/{TT.t}-{task-slug}/README.md` and `{NN}-{slug}.md`.
- Each milestone `plan.md` has a `## Tasks` table whose first column is the task number.

## Files

| Action | Path                             | Purpose |
|--------|----------------------------------|---------|
| Modify | `scripts/scaffold_provider.py`   | `plan_roadmap_stub()` and the `--task` auto-numbering |

## Symbols / fields

| Symbol                  | Kind     | Type / signature                                                                 | Default | Notes |
|-------------------------|----------|----------------------------------------------------------------------------------|---------|-------|
| `PROVIDER_SUBTASKS`     | constant | `tuple[tuple[str, str, str], ...]` (nn, slug, role)                              | see below | |
| `find_milestone_dir()`  | function | `(repo_root: Path, milestone: str) -> Path`                                      | - | Matches `docs/roadmap/<NNNN>-*`; exactly one or error |
| `next_task_number()`    | function | `(plan_md: Path) -> str`                                                         | - | Highest `NN.0` in the `## Tasks` table + 1 → `"05.0"` |
| `plan_roadmap_stub()`   | function | `(note: SourceNote, milestone_dir: Path, task: str) -> list[PlannedFile]`        | - | |

`PROVIDER_SUBTASKS`. This is the standard provider decomposition used across Milestone 0001:

| NN | slug                         | Role            |
|----|------------------------------|-----------------|
| 01 | `source-policy-gate`         | Architect       |
| 02 | `provider-metadata-and-metrics` | Python Expert |
| 03 | `fixtures-and-parser`        | Python Expert   |
| 04 | `normalization-aliases`      | Python Expert   |
| 05 | `validation-rules`           | Python Expert   |
| 06 | `registry-and-cli-wiring`    | Python Expert   |
| 07 | `contract-and-integration-tests` | Testing Expert |
| 08 | `provider-docs`              | Docs Writer     |

## Behaviour & validators

1. The task slug is the kebab-case of `display_name` plus `-provider`.
2. The stubs fill the template headers with real links, and body sections carry `TODO`
   markers.
3. Every generated link is absolute-from-repo-root, so
   `python3 scripts/check_doc_links.py <new folder>` passes on the generated stub.
4. The milestone's `plan.md` and `status.md` are **not** edited. The script prints the
   `## Tasks` and `## Current status` rows to paste in.

## Tests

Covered in [subtask 05](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/05-scaffold-tests.md)
(`test_roadmap_stub_*`).

## Success criteria

- [ ] With `--milestone 0001 --task 05.0`, the plan contains `README.md` + 8 subtask files
      under `docs/roadmap/0001-new-rating-providers/05.0-<slug>/`.

## Constraints

- Follows [docs/roadmap/README.md](/docs/roadmap/README.md) naming exactly
  (`{TT.t}` zero-padded).

## Out of scope

- Editing milestone tables (printed hint only).
