# Milestone 0007 - Source Research Tooling - Status

Tracks progress against [plan.md](/docs/roadmap/0007-source-research-tooling/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                    | Status         | Tests |
|------|-----------------------------------------|----------------|-------|
| 01.0 | Source Note Schema & Candidate Registry | ⬜ Not started | -     |
| 02.0 | Source Researcher Agent & Skill         | ⬜ Not started | -     |
| 03.0 | Read-only LangRank MCP Server           | ⬜ Not started | -     |
| 04.0 | Provider Intake Scaffold                | ⬜ Not started | -     |
| 05.0 | Source Watch Loop                       | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet. This milestone builds on these existing
pieces:

- the four prose source notes in `docs/source-notes/`;
- the agent/skill/loop fleet in `.claude/`;
- `scripts/check_doc_links.py`, the pattern for stdlib-only doc validators;
- the `github` and `playwright` MCP servers already registered in `.mcp.json`.

The seed research survey lives in
[docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md).

## Notes & decisions

- **Why a separate milestone:** research tooling is cross-cutting. It feeds
  [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) (which sources become
  providers next) and [Milestone 0004](/docs/roadmap/0004-freshness-and-releases/plan.md)
  (when sources publish). It does not belong to either one, and it adds no provider itself.
- **Order:** start with 01.0 (the schema), since 02.0, 04.0 and 05.0 depend on it. 03.0 is
  independent and can run in parallel. 05.0 lands last because it also needs the 02.0
  agent.
- **MCP SDK version:** specified against `mcp` 2.x (2.2.0 on PyPI, released 2026-09-07). The
  server class is `MCPServer` from `mcp.server` (1.x called it `FastMCP`). Tests use
  `mcp.Client(server)` in memory, and tool hints use snake_case
  `mcp.types.ToolAnnotations(read_only_hint=True)`. The dependency is pinned `mcp>=2.2,<3`
  in the optional extra.
- **Read-only is enforced, not promised:** the MCP server opens SQLite with `mode=ro` and
  bypasses `Database.__init__`, which currently always runs `migrate()` and
  `seed_languages()`. That is a write on every construction.
- **Stdlib-only scripts:** `check_source_notes.py`, `scaffold_provider.py` and
  `source_calendar.py` use a restricted YAML front-matter subset parser rather than adding
  PyYAML, matching the no-dependency convention of the existing `scripts/`.

## Decomposition tree (as planned)

```
docs/roadmap/0007-source-research-tooling/
├── plan.md
├── status.md
├── 01.0-source-note-schema-and-candidate-registry/
│   ├── README.md
│   ├── 01-front-matter-schema-and-template.md
│   ├── 02-source-notes-validator.md
│   ├── 03-backfill-existing-source-notes.md
│   ├── 04-candidate-registry-generation.md
│   └── 05-ci-and-hook-wiring.md
├── 02.0-source-researcher-agent-and-skill/
│   ├── README.md
│   ├── 01-source-researcher-agent-definition.md
│   ├── 02-source-research-skill.md
│   ├── 03-web-ingestion-security-review.md
│   └── 04-agent-and-skill-reference-docs.md
├── 03.0-read-only-mcp-server/
│   ├── README.md
│   ├── 01-tool-contract-adr.md
│   ├── 02-read-only-database-mode.md
│   ├── 03-optional-extra-and-cli-command.md
│   ├── 04-query-tools.md
│   ├── 05-source-note-resources.md
│   ├── 06-mcp-server-tests.md
│   ├── 07-threat-model.md
│   └── 08-registration-and-usage-docs.md
├── 04.0-provider-intake-scaffold/
│   ├── README.md
│   ├── 01-scaffold-templates.md
│   ├── 02-scaffold-script.md
│   ├── 03-roadmap-task-stub-generation.md
│   ├── 04-provider-scaffold-skill.md
│   └── 05-scaffold-tests.md
└── 05.0-source-watch-loop/
    ├── README.md
    ├── 01-edition-calendar-script.md
    ├── 02-source-watch-loop-definition.md
    ├── 03-issue-drafting-and-dedup.md
    └── 04-scheduling-and-lifecycle-review.md
```

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name (status, date)`
subsection per task with a **Delivered** list and a **Tests / gate** summary._
