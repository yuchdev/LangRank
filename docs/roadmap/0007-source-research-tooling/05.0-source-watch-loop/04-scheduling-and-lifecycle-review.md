# Subtask 05.0/04 - Scheduling & Lifecycle Review

**Task:** [05.0 - Source Watch Loop](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/README.md) ·
**Role:** Architect · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Document how to run the watch on a schedule: locally through `/loop`, or remotely through a
`/schedule` routine. Get an `incident-analyst` review confirming that every lifecycle
transition has both a success exit and a failure exit.

## Baseline

- `incident-analyst` reviews state machines with a human-escalation path.
- `/schedule` creates cron-based cloud routines, and `/loop` self-paces locally.

## Files

| Action | Path                                                    | Purpose |
|--------|---------------------------------------------------------|---------|
| Create | `docs/agent/source-watch.md`                            | Runbook: weekly schedule suggestion (Monday 09:00 local), local vs routine setup, required secrets (`GITHUB_PERSONAL_ACCESS_TOKEN` only when filing issues), how to review drafts |
| Create | `docs/reviews/source-watch-lifecycle-review.md`         | incident-analyst output |
| Modify | `docs/README.md`                                        | Registry entry for the runbook |
| Modify | `docs/agent/tutorial.md`                                | Link from the "Researching a new ranking source" section (Task 02.0/04) |

## Symbols / fields

The lifecycle table that the review must confirm:

| From        | Event                       | To            | Human-visible artifact |
|-------------|-----------------------------|---------------|------------------------|
| due         | freshness/researcher: new   | new-edition   | Branch + issue draft |
| due         | researcher: same edition    | unchanged     | `last_verified` bump on branch |
| due         | cadence exceeded, none found| overdue       | Issue draft |
| due         | any failure                 | error         | Issue draft with error |
| any         | loop interrupted            | resumable     | Run state file lists pending sources |

## Behaviour & validators

1. The review verdict is `PASS` only if no path ends without a human-visible artifact and
   `error` is never retried silently more than once.
2. The runbook states that routines run with `--no-issues` until a human has approved the
   first three dry runs.

## Tests

None (docs and review).

## Success criteria

- [ ] The runbook and review exist, and the review verdict is `PASS`.
- [ ] `python3 scripts/check_doc_links.py docs/agent docs/reviews docs/README.md` reports no
      new problems.

## Constraints

- No secrets in docs. Reference the env var names only.

## Out of scope

- Auto-merging drafts. This is permanently out of scope per
  [plan.md § Human in the loop](/docs/roadmap/0007-source-research-tooling/plan.md#human-in-the-loop).
