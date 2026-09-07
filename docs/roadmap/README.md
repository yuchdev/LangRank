# LangRank Roadmap

Planning and progress tracking for LangRank, organised as a three-tier
hierarchy: **Milestone → Task → Subtask**.

## Hierarchy & vocabulary

| Tier          | Meaning                                                                                                       | Lives in                                                |
|---------------|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| **Milestone** | A large, strategic initiative / development direction (e.g. the generic implementation effort).               | A folder `docs/roadmap/{NNNN}-{milestone-slug}/`.       |
| **Task**      | One deliverable unit of a milestone (e.g. "AWS Bedrock Backend"). Listed in the milestone's `## Tasks` table. | A subfolder `…/{TT.t}-{task-slug}/` with a `README.md`. |
| **Subtask**   | An atomic, implementable spec (one file, one set of classes/tests). Listed in the task's `## Subtasks` table. | A file `…/{TT.t}-{task-slug}/{NN}-{subtask-slug}.md`.   |

A *subtask* is part of a *task*; a *task* is part of a *milestone*.

## File & folder convention

```
docs/roadmap/
  README.md                              ← this index + convention
  {NNNN}-{milestone-slug}/               ← MILESTONE
    plan.md                              ← milestone spec; opens with a `## Tasks` table
    status.md                            ← progress tracker (optional); `## Current status` table
    {TT.t}-{task-slug}/                  ← TASK
      README.md                          ← task spec; opens with a `## Subtasks` table
      {NN}-{subtask-slug}.md             ← SUBTASK spec
```

- `{NNNN}` - zero-padded milestone number (`0001`, `0002`, …).
- `{TT.t}` - task number, carried from the milestone's `## Tasks` table (e.g. `03.2`, `06.1`, `08.0`).
- `{NN}` - zero-padded subtask order (`01`, `02`, …).
- Slugs are kebab-case.

### Heading vocabulary

- A milestone's `plan.md` lists its tasks under a `## Tasks` heading (table column: `Task`).
- A task's `README.md` lists its subtasks under a `## Subtasks` heading.
- Avoid "Phase" for these tiers - it is reserved for the product-vision phases in
  [docs/roadmap/roadmap.md](/docs/roadmap/roadmap.md) (usually require months) and would otherwise be ambiguous.

### Linking convention

When a document references another **specific** document, use an
absolute-from-repo-root Markdown link:

```
[docs/roadmap/0001-new-rating-providers/plan.md](/docs/roadmap/0001-new-rating-providers/plan.md)
```

- Always a leading `/` (repo root), never relative `../../` chains.
- **Template** paths (containing `{` / `}`, e.g. `` `{NN}-{subtask-slug}.md` ``) stay as
  backtick code spans, not links.
- Run `python scripts/check_doc_links.py docs/` (or the `/link-check` skill) to verify every
  link target and `#heading-anchor` resolves. The `doc_link_check` hook runs it on edits.

## Milestones

These six milestones were split out of an earlier single
`0001-generic-implementation` umbrella document once it grew several
distinct development directions. 0001 is the foundation the other five build
on to varying degrees (see each milestone's own "Depends on" line); 0002-0006
are mostly independent of each other, with the soft dependencies noted below.

| #    | Milestone                   | Depends on                  | Spec                                                                       | Status                                                                       |
|------|------------------------------|------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| 0001 | New rating providers         | -                            | [plan.md](/docs/roadmap/0001-new-rating-providers/plan.md)                  | [status.md](/docs/roadmap/0001-new-rating-providers/status.md)                |
| 0002 | Cross-rating analysis        | 0001 (soft)                  | [plan.md](/docs/roadmap/0002-cross-rating-analysis/plan.md)                 | [status.md](/docs/roadmap/0002-cross-rating-analysis/status.md)               |
| 0003 | Historical data quality      | -                            | [plan.md](/docs/roadmap/0003-historical-data-quality/plan.md)               | [status.md](/docs/roadmap/0003-historical-data-quality/status.md)             |
| 0004 | Freshness & releases         | 0001, 0003 (soft)            | [plan.md](/docs/roadmap/0004-freshness-and-releases/plan.md)                | [status.md](/docs/roadmap/0004-freshness-and-releases/status.md)              |
| 0005 | CLI & storage enhancements   | 0001 (soft, Task 03.0 only)  | [plan.md](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md)          | [status.md](/docs/roadmap/0005-cli-and-storage-enhancements/status.md)        |
| 0006 | Provider extensibility       | -                            | [plan.md](/docs/roadmap/0006-provider-extensibility/plan.md)                | [status.md](/docs/roadmap/0006-provider-extensibility/status.md)              |
