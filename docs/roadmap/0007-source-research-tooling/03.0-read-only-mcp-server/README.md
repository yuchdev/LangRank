# Task 03.0 - Read-only LangRank MCP Server

**Milestone:** [0007 - Source Research Tooling](/docs/roadmap/0007-source-research-tooling/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0007-source-research-tooling/plan.md#task-030---read-only-langrank-mcp-server) ·
**Category:** integration · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                        | Role             | Depends on | Status         |
|----|--------------------------------------------------------------------------------------------------------------------------------|------------------|------------|----------------|
| 01 | [Tool contract ADR](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/01-tool-contract-adr.md)                | Architect        | -          | ⬜ Not started |
| 02 | [Read-only database mode](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/02-read-only-database-mode.md)    | Python Expert    | 01         | ⬜ Not started |
| 03 | [Optional extra & `mcp serve` command](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/03-optional-extra-and-cli-command.md) | Python Expert | 02 | ⬜ Not started |
| 04 | [Query tools](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/04-query-tools.md)                            | Python Expert    | 03         | ⬜ Not started |
| 05 | [Source-note resources](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/05-source-note-resources.md)        | Python Expert    | 03         | ⬜ Not started |
| 06 | [MCP server tests](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/06-mcp-server-tests.md)                  | Testing Expert   | 04, 05     | ⬜ Not started |
| 07 | [Threat model](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/07-threat-model.md)                          | Security Auditor | 04, 05     | ⬜ Not started |
| 08 | [Registration & usage docs](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/08-registration-and-usage-docs.md) | Docs Writer   | 06, 07     | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Expose the local LangRank SQLite database to MCP clients (Claude Code, the source-researcher
agent, IDE assistants) as a small set of **read-only**, provenance-carrying tools. This is
how research agents ground their recommendations in what LangRank already stores:

- **Coverage gaps:** "RedMonk has no 2019-Q3 point; is that a source gap or ours?" uses
  `coverage` plus `query_observations`.
- **Overlap check:** before a candidate source is recommended, `list_ratings` and
  `list_metrics` show whether a stored rating already measures the same thing (e.g. a
  second self-reported-usage survey).
- **Sanity comparison:** a researcher reads a candidate's published top-10 and compares its
  *order* against stored series with `query_observations`, or with `compare_normalized` once
  [Milestone 0002](/docs/roadmap/0002-cross-rating-analysis/plan.md) has landed. It never
  compares raw values across ratings.
- **Naming quirks:** `resolve_language` shows how a source label ("Golang", "C/C++") maps to
  a canonical ID before a note records it as a quirk.
- **Methodology context:** `methodology_notes` plus the `langrank://source-notes/{id}`
  resources put the stored methodology and the research note side by side.

## Baseline (what already exists)

- `src/langrank/db/repository.py`:
  - `Database.__init__` **always** calls `migrate()` and `seed_languages()`, which are
    writes;
  - `Database.connect()` opens a plain read-write `sqlite3.connect(self.db_path)`.
- `src/langrank/cli.py`: `main_callback` builds `AppState`, whose `__init__` constructs
  `Database(config.db_path)` eagerly, so any subcommand, including a future `mcp serve`,
  currently writes to the DB on startup.
- Read methods that already exist:
  - `Database.list_ratings`
  - `list_metrics`
  - `list_methodology_notes`
  - `list_languages`
  - `list_aliases`
  - `alias_to_language`
  - `language_suggestions`
  - `coverage`
  - `query_rows`
  - `latest_observation_for_provider`

  Service-level reads:
  - `services/query.py:QueryService.query`
  - `services/status.py:StatusService.statuses`
- `QueryRow` lacks the provenance fields `parser_version`, `is_derived`,
  `derivation_method`, `retrieved_at`, `source_document_id` and `source_published_at`.
  A new read query is needed.
- Latent bug to be aware of: `QueryService._apply_top_filters` compares `metric_id == "rank"`,
  but production metric IDs are provider-prefixed (`tiobe-rank`, …). The MCP tools must not
  expose `top`/`top_current` until that is fixed in
  [Milestone 0005 Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-050---historical-selection-semantics).
- `.mcp.json` registers `github` and `playwright` (both `npx`).
- The SDK is `mcp` 2.x on PyPI (2.2.0, 2026-09-07). The current API is:
  - `from mcp.server import MCPServer`;
  - `@server.tool(title=..., annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))`;
  - `@server.resource("scheme://{param}")`;
  - `server.run()`, whose default transport is stdio;
  - in-memory testing through `from mcp import Client`, then
    `async with Client(server, raise_exceptions=True) as c: await c.call_tool(...)`.

  1.x called the server class `FastMCP` (in `mcp.server.fastmcp`), and it is not used here.

## Design notes

- **Optional extra, lazy import.** The `mcp` SDK is a sizeable dependency tree. Core
  `langrank` users must not pay for it, and CI's default `uv sync --frozen` must still pass
  without it.
- **Read-only by construction, not by convention.** The server gets a `Database` created
  with `read_only=True`. That mode:
  - never migrates or seeds;
  - opens `file:<path>?mode=ro` with `uri=True`;
  - fails fast if the file is missing or its schema version is older than `SCHEMA_VERSION`.

  The MCP code imports no write method.
- **Tools reuse repository/service reads.** The server module holds no SQL. The one new
  query (provenance-carrying observations) lives in `Database` per [CLAUDE.md](/CLAUDE.md).
- **Bounded output.** `query_observations` defaults to 500 rows and caps at 5000. A
  truncated response carries `truncated: true` and the total count.
- **Caveat field.** Any response that spans more than one `rating_id` includes
  `caveat: "Values from different ratings measure different things and are not comparable without explicit normalization."`
- **No network, no fetch.** There are no tools that call providers, `FetchService`, or
  import. `open_world_hint=False` is set on every tool.

### Open questions

- Should the HTTP transport (`streamable-http`) be exposed? **Default: no.** stdio only. A
  local HTTP listener adds an auth surface with no current need.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `langrank mcp serve` works from Claude Code through `.mcp.json`, and all tools are listed.
- [ ] Any write through the server's DB connection raises `sqlite3.OperationalError` (tested).
- [ ] Without the extra, `langrank mcp serve` exits 2 with an install hint.
- [ ] The threat model has no open CRITICAL findings.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green, both with and without the extra.

## References

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk · docs https://py.sdk.modelcontextprotocol.io/ (testing: https://py.sdk.modelcontextprotocol.io/get-started/testing/) · PyPI https://pypi.org/project/mcp/
- [docs/architecture.md](/docs/architecture.md), [docs/data-model.md](/docs/data-model.md)
