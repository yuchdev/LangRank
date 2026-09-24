# Task {TT.t} - {Task Name}

**Milestone:** [{NNNN} - {Milestone Name}](/docs/roadmap/{NNNN}-{milestone-slug}/plan.md) ·
**Spec source:** [plan.md § Task {TT.t}](/docs/roadmap/{NNNN}-{milestone-slug}/plan.md#task-{TTt}---{task-slug}) ·
**Category:** {category} · **Status:** ⬜ Not started

> Template - copy to `docs/roadmap/{NNNN}-{milestone-slug}/{TT.t}-{task-slug}/README.md`.
> The `## Subtasks` table must stay the first `##` section after the header: the
> `implement-subtasks` loop parses it (columns `#`, `Subtask`, `Role`, `Depends on`, `Status`).
> `Role` uses the loop's roster keywords: `Architect`, `Python Expert`, `Testing Expert`,
> `Security Auditor`, `Docs Writer`.

## Subtasks

| #  | Subtask                                                                                   | Role          | Depends on | Status         |
|----|-------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [{Subtask title}](/docs/roadmap/{NNNN}-{milestone-slug}/{TT.t}-{task-slug}/01-{slug}.md) | Python Expert | -          | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

One paragraph: what the task delivers and why, restating the plan.md goal in implementation terms.

## Baseline (what already exists)

Bullets naming real files/symbols (`src/langrank/...:Symbol`) that this task builds on or
changes. Call out anything the plan assumes is missing but which already exists, and any
latent bug the task must fix or work around.

## Design notes

Key decisions, with the reason for each. Open questions go in a `### Open questions`
sub-list with a proposed default so an implementer is never blocked.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Task-level success criteria from plan.md (restated as checkboxes).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

External sources, ADRs, source notes (`docs/source-notes/...`), research docs.
