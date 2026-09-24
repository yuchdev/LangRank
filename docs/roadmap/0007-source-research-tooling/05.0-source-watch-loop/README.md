# Task 05.0 - Source Watch Loop

**Milestone:** [0007 - Source Research Tooling](/docs/roadmap/0007-source-research-tooling/plan.md) ·
**Spec source:** [plan.md § Task 05.0](/docs/roadmap/0007-source-research-tooling/plan.md#task-050---source-watch-loop) ·
**Category:** agentic · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                | Role           | Depends on          | Status         |
|----|----------------------------------------------------------------------------------------------------------------------------------------|----------------|---------------------|----------------|
| 01 | [Edition calendar script](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/01-edition-calendar-script.md)                | Python Expert  | Task 01.0           | ⬜ Not started |
| 02 | [source-watch loop definition](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/02-source-watch-loop-definition.md)      | Architect      | 01, Task 02.0       | ⬜ Not started |
| 03 | [Issue drafting & de-duplication](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/03-issue-drafting-and-dedup.md)       | Python Expert  | 02                  | ⬜ Not started |
| 04 | [Scheduling & lifecycle review](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/04-scheduling-and-lifecycle-review.md)  | Architect      | 03                  | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Notice, on a schedule, that a tracked source has probably published a new edition, or
has gone quiet for longer than its cadence allows. Hand a human a drafted source-note
update and, optionally, a de-duplicated GitHub issue.

The loop never runs `langrank fetch`, never writes to the database, never commits to the
default branch, and never closes or merges anything.

## Baseline (what already exists)

- Loop format: `.claude/loops/*.md` with front matter `name`, `description`, `invoke` and
  `terminates-when`, numbered steps, and `ScheduleWakeup` rescheduling. See
  `.claude/loops/update-docs.md` and `implement-subtasks.md`.
- `.mcp.json` registers the `github` MCP server, and `.claude/hooks/github_audit.py` audits
  every `mcp__github__*` call.
- `src/langrank/services/status.py:StatusService.statuses()` gives `upstream_latest_period`,
  but that value is **hard-coded per provider** (e.g. `TiobeProvider.upstream_latest_period()`
  returns `"2025-12"`). It is no real freshness signal until
  [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates)
  lands.
- Front-matter fields from Task 01.0: `cadence`, `typical_publication_month`,
  `last_verified`, `status`, and `provider_id`.
- The `source-researcher` agent comes from Task 02.0; it runs `verify` mode through
  `/source-research <id> --verify`.

## Design notes

- **Calendar first, network second.** A deterministic script decides which sources are
  *due*. Only due sources get a web check, which keeps request volume tiny and respects the
  sources' terms.
- **Lifecycle with explicit exits.** Every due source ends in exactly one state:
  - `new-edition` → a drafted note update on a branch, plus an optional issue;
  - `unchanged` → no change except `last_verified`;
  - `overdue` → the cadence was exceeded with no edition found; an issue is drafted;
  - `error` → reported, never swallowed.

  The `incident-analyst` agent reviews this machine in subtask 04.
- **Soft dependency on Milestone 0004.** Once real freshness checks exist
  (`langrank status --json`), the loop uses them for `existing` providers before falling
  back to researcher checks.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] With frozen `today` and fixture notes, `source_calendar.py` selects exactly the expected
      due sources.
- [ ] `/loop source-watch --dry-run` produces issue drafts without calling GitHub.
- [ ] Two runs on the same day file no duplicate issues.
- [ ] The incident-analyst review shows every transition has a success and a failure exit.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- Typical calendars, which the notes must confirm:
  - RedMonk: roughly Q1 and Q3 editions;
  - Stack Overflow Developer Survey: results around July;
  - IEEE Spectrum: around August-September;
  - GitHub Octoverse: around October-November;
  - JetBrains State of Developer Ecosystem: around mid-year to December;
  - TIOBE and PYPL: monthly.

  See [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md).
