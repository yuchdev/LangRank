# Subtask 02.0/02 - /source-research Skill

**Task:** [02.0 - Source Researcher Agent & Skill](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/README.md) ·
**Role:** Architect · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Create `.claude/skills/source-research/SKILL.md`. The skill resolves its argument, spawns
`source-researcher`, enforces the write scope, runs the validator and registry check, and
returns a scorecard.

## Baseline

- The skill format is in `.claude/skills/pr-review/SKILL.md`: front matter with `name`,
  `description`, `allowed-tools` and `invocation`, then `## Steps`, an output block, and a
  `## Completion checklist`.

## Files

| Action | Path                                                   | Purpose |
|--------|--------------------------------------------------------|---------|
| Create | `.claude/skills/source-research/SKILL.md`              | Skill definition |
| Create | `.claude/skills/source-research/references/scorecard.md` | Scorecard output format and rubric quick reference (links to `docs/source-notes/README.md`) |

## Symbols / fields

| Symbol          | Kind         | Value | Notes |
|-----------------|--------------|-------|-------|
| `name`          | front matter | `source-research` | |
| `invocation`    | front matter | `/source-research <source-id\|url\|"topic"> [--verify]` | |
| `allowed-tools` | front matter | `Read, Grep, Glob, Bash, Agent` | The skill itself does not use web tools; the agent does |

## Behaviour & validators

`## Steps`:

1. **Resolve the argument.**
   - An existing `docs/source-notes/<id>.md` → mode `update`, or `verify` with `--verify`.
   - A URL → match it against note `homepage`s; with no match, mode `new`.
   - Anything else is a topic → mode `new`, and the agent may create several `candidate`
     notes (at most 5 per run).
2. **Snapshot.** Run `git status --porcelain` before spawning.
3. **Spawn** `source-researcher` with the mode, the argument, and the note path(s).
4. **Scope check.** Diff `git status --porcelain` against the snapshot. If any changed path
   lies outside `docs/source-notes/` and `docs/research/`, report **SCOPE VIOLATION**, list
   the paths, and do *not* revert them automatically. The human decides.
5. **Validate.** Run `python scripts/check_source_notes.py --check`. On failure, send the
   problems back to the agent once. If it still fails, report the failure.
6. **Registry.** Run `python scripts/check_source_notes.py --check-registry`. If it is
   stale, run `--write-registry` and include that in the change list.
7. **Scorecard.** Return it in the format from `references/scorecard.md`:
   - the note path(s);
   - `measures`;
   - the six scores and their total;
   - the recommended `status`/`priority`;
   - the `(unverified)` field count;
   - whether it overlaps an existing provider's measurement type;
   - suggested next step: `/provider-scaffold` (Task 04.0) when the recommendation is
     `planned`.

`## Completion checklist` items:

- [ ] Validator exit 0.
- [ ] Registry current.
- [ ] No scope violation.
- [ ] Every new note has ≥ 1 URL in `## Sources`.
- [ ] Nothing committed. The skill never runs `git commit`.

## Tests

No pytest. Acceptance runs are recorded in the PR description:

| Acceptance run                                             | Expected |
|------------------------------------------------------------|----------|
| `/source-research ieee-spectrum`                           | Mode `update`; validator 0; scorecard shows `measures: composite` |
| `/source-research "job-posting based language demand indices"` | Mode `new`; 1-5 `candidate` notes; registry regenerated |
| `/source-research tiobe --verify`                          | Only `last_verified` and `## Sources` change unless facts changed |

## Success criteria

- [ ] `.claude/skills/source-research/SKILL.md` exists with all 7 steps and the completion checklist.
- [ ] The three acceptance runs are recorded in the PR.

## Constraints

- The skill never commits, pushes, or opens PRs. Those decisions belong to a human.

## Out of scope

- Scheduled or recurring research: [Task 05.0](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/README.md).
