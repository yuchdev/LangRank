# Subtask 04.0/04 - /provider-scaffold Skill

**Task:** [04.0 - Provider Intake Scaffold](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/README.md) ·
**Role:** Architect · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Create `.claude/skills/provider-scaffold/SKILL.md`. It wraps the script: dry run first,
confirm with the user, apply, then point at the implement loop.

## Baseline

- Skill format: `.claude/skills/*/SKILL.md` front matter + `## Steps` + `## Completion checklist`.
- `.claude/loops/implement-subtasks.md` drives a decomposed task.

## Files

| Action | Path                                           | Purpose |
|--------|------------------------------------------------|---------|
| Create | `.claude/skills/provider-scaffold/SKILL.md`    | Skill |
| Modify | `docs/agent/skills.md`                         | Reference row |

## Symbols / fields

| Symbol          | Kind         | Value |
|-----------------|--------------|-------|
| `name`          | front matter | `provider-scaffold` |
| `invocation`    | front matter | `/provider-scaffold <source-id> [--milestone NNNN] [--task TT.t]` |
| `allowed-tools` | front matter | `Read, Grep, Glob, Bash` |

## Behaviour & validators

Steps:

1. Run `python scripts/check_source_notes.py --check docs/source-notes/<id>.md`. Stop on
   failure.
2. Run the script with `--dry-run` and show the plan.
3. Ask the user to confirm. This is the only point where files get created.
4. Apply, then print the registry/alias hints and the milestone table rows verbatim.
5. Suggest `/loop implement-subtasks <milestone>/<task>` as the next step.

Checklist:

- [ ] The gate passed.
- [ ] The user confirmed.
- [ ] No existing file was modified (`git status --porcelain` shows only `??` new paths).

## Tests

No pytest (prompt file). Acceptance run recorded in the PR:
`/provider-scaffold ieee-spectrum --milestone 0001 --task 03.0` after Milestone 0001's
Task 03.0 folder exists. Expected result: every file `SKIP`s except the missing ones.

## Success criteria

- [ ] The skill file exists with the 5 steps and the checklist, and a `docs/agent/skills.md`
      row is added.

## Constraints

- The skill never commits.

## Out of scope

- Implementing the provider (the `implement-subtasks` loop and `python-expert` do that).
