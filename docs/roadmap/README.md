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
  a future `docs/roadmap/roadmap.md` (usually require months) and would otherwise be ambiguous.

### Templates

New task folders and subtask specs start from the templates in `docs/roadmap/_templates/`:

- [task-readme.md](/docs/roadmap/_templates/task-readme.md) - task `README.md`; the `## Subtasks`
  table (columns `#`, `Subtask`, `Role`, `Depends on`, `Status`) is what the
  `implement-subtasks` loop parses.
- [subtask.md](/docs/roadmap/_templates/subtask.md) - subtask spec; its sections (Files,
  Symbols / fields, Behaviour & validators, Tests, Success criteria, Constraints) map 1:1 onto
  the `subtask-verifier` agent's compliance matrix.

The `_templates/` folder name deliberately does not match `{NNNN}-*`, so roadmap tooling never
mistakes it for a milestone.

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

Milestones 0001-0006 were split out of an earlier single
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
| 0007 | Source research tooling      | 0001, 0002, 0004 (soft)      | [plan.md](/docs/roadmap/0007-source-research-tooling/plan.md)               | [status.md](/docs/roadmap/0007-source-research-tooling/status.md)             |

Every task in 0001-0007 is decomposed into a `{TT.t}-{task-slug}/` folder with a `README.md`
and `{NN}-{subtask-slug}.md` specs. Milestone 0007 adds the agentic research tooling (a
source-researcher agent, a read-only LangRank MCP server, provider scaffolding, and a
source-watch loop); its seed dataset is the source survey in
[docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md).

## Cross-milestone defect ledger

Defects found in the current code while the milestones were broken down (2026-09-24/25). Each
has **exactly one** owning subtask, and other milestones link to that owner instead of fixing
the defect again.

| # | Defect (current code)                                                                                                                                          | Owner                                                                                                                                                  | Also touched by (reuse, don't re-fix)                                                                                                                                                                            |
|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | Bare `"rank"` metric-ID comparisons (`QueryService._apply_top_filters`, `validation_queries['invalid_ranks']`, `PlotService` inversion, `plot --metric` default) only work for `demo` | [0006 01.0/02](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/02-metric-role-lookups.md) (final, `MetricKind`)                | Interim `Database.rank_metric_ids()`: [0005 02.0/02](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/02-rank-metric-resolution-fix.md), [0003 03.0/01](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/01-quality-framework.md) |
| 2 | `stackoverflow-survey-rank` is computed by LangRank but stored `is_derived=False`                                                                              | [0006 01.0/07](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/07-derived-rank-provenance.md)                                  | -                                                                                                                                                                                                                |
| 3 | `methodology_notes` unique key includes `valid_from`/`valid_to`, so editing a bound inserts a duplicate                                                         | [0003 01.0/03](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/03-methodology-note-sync.md)                                       | -                                                                                                                                                                                                                |
| 4 | Hard-coded `upstream_latest_period()` values; `StatusService` probes with `hasattr`                                                                              | [0004 01.0/03](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/03-provider-freshness-probes.md) (values)                          | [0006 01.0/04](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/04-status-service-capabilities.md) (replaces `hasattr`)                                                             |
| 5 | Two alias-resolution paths (`LanguageNormalizer.resolve` in providers vs `Database.alias_to_language`); rating-scoped and date-bounded aliases ignored            | [0003 02.0/03](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/03-date-aware-resolution.md)                            | [0005 04.0](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) (read-only `languages resolve`), [0001 01.0](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) (`try_resolve`) |
| 6 | `payload_from_content` never fills `RawArtifact.http_etag` / `http_last_modified`; `HttpClientFactory` unused (providers read bundled CSVs)                     | [0004 01.0/02](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/02-conditional-http-probe.md)                                     | Each 0001 provider's fetch subtask                                                                                                                                                                               |
| 7 | `Database.__init__` always migrates and seeds (writes), so there is no read-only mode                                                                           | [0007 03.0/02](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/02-read-only-database-mode.md)                                            | 0003 03.0 (`connect_readonly()` - reuse the same mode)                                                                                                                                                           |
| 8 | Template leftovers: `.coveragerc` `source = src/aegis_swr`; coverage 73% vs the 85% floor; CI has no coverage gate                                              | [0005 06.0](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md)                                                           | -                                                                                                                                                                                                                |
| 9 | `langrank import` bypasses `FetchService` (no `raw_artifacts` row, and it duplicates the validate-then-upsert logic)                                             | **Unowned** - proposed: fold into [0006 01.0/03](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/03-provider-capabilities-model.md) (`supports_manual_import`) | 0004 02.0 (release provenance)                                                                                                                                                                                   |

Already fixed upstream (PR #4, "Fix formatter and mypy failures to restore CI"): the ruff `B008`
false positives on Typer defaults, repository-wide `ruff format`, and the missing `pydantic.mypy`
plugin in `mypy.ini`.
