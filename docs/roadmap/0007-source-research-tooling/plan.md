# Milestone 0007 - Source Research Tooling

**Package:** `langrank` | **Module root:** `docs/source-notes/`, `.claude/`, `scripts/`, `src/langrank/mcp/`
**Depends on:** nothing hard. Soft dependencies:
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) (more providers make the
MCP server's coverage/comparison answers more useful),
[Milestone 0002](/docs/roadmap/0002-cross-rating-analysis/plan.md) (the optional
`compare_normalized` MCP tool reuses its `rank_percentile` normalization), and
[Milestone 0004](/docs/roadmap/0004-freshness-and-releases/plan.md) (the source-watch loop
reuses its cheap freshness checks once they exist).

Finding, vetting, and tracking language-ranking sources is ongoing work, not a one-off:
sources publish new editions on their own calendars (RedMonk twice a year, the Stack Overflow
survey each summer, IEEE Spectrum each autumn, Octoverse each autumn/winter), change
methodology, change terms, or go defunct. The seed survey in
[docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md) is a
snapshot. This milestone turns that research into a repeatable, agent-assisted workflow:

1. a machine-checkable **source-note schema** so every source (existing, planned, candidate,
   rejected, defunct) is described the same way and scored on one rubric;
2. a **source-researcher agent** + `/source-research` skill that writes and updates those notes
   from cited web research;
3. a **read-only LangRank MCP server** so any agent can interrogate the local database
   (coverage, gaps, provenance, methodology) while researching, without shelling out or writing;
4. a **provider intake scaffold** that turns a vetted note into a provider skeleton + roadmap
   task stub;
5. a **source-watch loop** that uses the notes' publication calendar to notice new editions and
   hand a human a drafted update.

It adds no new rating provider and changes no stored data. Everything here either documents
sources or reads the database.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                   | Category      | Output                                                                                     |
|------|----------------------------------------|---------------|--------------------------------------------------------------------------------------------|
| 01.0 | Source Note Schema & Candidate Registry | research-docs | Front-matter schema, `TEMPLATE.md`, `scripts/check_source_notes.py`, `docs/research/source-candidates.md` |
| 02.0 | Source Researcher Agent & Skill         | agentic       | `.claude/agents/source-researcher.md`, `/source-research` skill                              |
| 03.0 | Read-only LangRank MCP Server           | integration   | `src/langrank/mcp/server.py`, `langrank mcp serve`, optional extra `langrank[mcp]`          |
| 04.0 | Provider Intake Scaffold                | agentic       | `scripts/scaffold_provider.py`, `/provider-scaffold` skill                                  |
| 05.0 | Source Watch Loop                       | agentic       | `scripts/source_calendar.py`, `.claude/loops/source-watch.md`                               |

Task decomposition: [01.0](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/README.md) ·
[02.0](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/README.md) ·
[03.0](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
[04.0](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/README.md) ·
[05.0](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/README.md)

Dependencies: Tasks 02.0, 04.0 and 05.0 all consume the schema from Task 01.0, so 01.0 lands
first. Task 05.0 also delegates drafting to the agent from Task 02.0. Task 03.0 (MCP server) is
independent and can proceed in parallel with everything else. Task 02.0's agent *uses* the MCP
server when it is registered, but works without it.

---

## Shared conventions

### Research is documentation, never data

No task in this milestone writes to the SQLite database or triggers `langrank fetch`. Agents
produce Markdown (source notes, registry, issue drafts); the MCP server is read-only by
construction (Task 03.0). Turning a researched source into stored observations always goes
through a normal provider task and its
[legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).

### Cite or mark unverified

Every factual claim in a source note (history start, license, cadence, access method) carries
either a URL cited in the note's `## Sources` section or an explicit `(unverified)` marker.
`last_verified` in the front matter is the date a human or the researcher agent last checked
the cited URLs, not the date the file was edited.

### Respect source terms during research

Research agents read public pages only: no logging in, no CAPTCHA or paywall circumvention, no
bulk crawling. robots.txt and terms of use are *recorded* in the note (`terms_url`,
`automation`), since they feed the provider gate later.

### Human in the loop

Agentic tasks (02.0, 04.0, 05.0) draft; humans merge. No loop auto-commits to the default
branch, auto-merges a PR, or closes an issue. Fetched web content is untrusted input: an agent
never follows instructions found inside a fetched page.

### Measurement-type honesty

Every note declares what the source actually `measures` (search visibility, tutorial search,
Q&A activity, code-hosting activity, self-reported usage, job demand, composite). The registry
and MCP outputs keep that label next to every number, following the project's rule that ratings
are not comparable across providers without explicit normalization (see [CLAUDE.md](/CLAUDE.md)).

### Testing

Scripts under `scripts/` stay stdlib-only (like `scripts/check_doc_links.py`) and get tests
under `tests/scripts/`. The MCP server gets in-memory client tests that skip cleanly when the
optional extra is not installed. `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy src`, and `uv run pytest` stay clean throughout.

---

## Per-task specifications

### Task 01.0 - Source Note Schema & Candidate Registry

**Goal:** one machine-checkable description format for every language-ranking source, so a
source can be compared, prioritized, scheduled and scaffolded without re-reading prose.

- YAML front matter on every `docs/source-notes/*.md`, with these fields: `source_id`,
  `provider_id` (null until registered), `display_name`, `status`
  (`existing|planned|candidate|rejected|defunct`), `measures`, `access`, `license`,
  `terms_url`, `automation`, `history_start`, `granularity`, `cadence`,
  `typical_publication_month`, `homepage`, `last_verified`, `priority`, `roadmap`, and a
  `scores` map covering the rubric dimensions.
- `docs/source-notes/TEMPLATE.md` plus a scoring rubric (the dimensions, and a 1-5 anchor
  description for each score).
- Backfill the four existing notes (`tiobe`, `pypl`, `redmonk`, `stackoverflow-survey`) and
  add notes for the four [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md)
  sources as `planned`.
- `scripts/check_source_notes.py` is a stdlib-only validator. It parses a restricted YAML
  subset and also generates or checks `docs/research/source-candidates.md`, the registry
  table sorted by status and priority.
- Wire the validator into CI and a PostToolUse hook, the same way `doc_link_check` is wired.

**Success criteria:** `python scripts/check_source_notes.py --check` exits 0 on the
backfilled notes and exits 1 with a file:line message for each seeded defect. The registry is
regenerated deterministically, and CI fails if it is stale.

---

### Task 02.0 - Source Researcher Agent & Skill

**Goal:** an agent that researches a named source or an open topic ("job-posting based
language indices") and writes cited, schema-valid source notes. It never touches code or data.

- `.claude/agents/source-researcher.md`:
  - Tools: `WebSearch`, `WebFetch`, `Read`, `Grep`, `Glob`, `Write`, `Edit`, `Bash`.
    `Bash` is limited by instructions to running `scripts/check_source_notes.py`.
  - Writes only under `docs/source-notes/` and `docs/research/`.
  - Model: `claude-sonnet-4-6`, matching the other research/review agents.
- `/source-research <source-id|url|"topic">` skill. It resolves the argument, spawns the
  agent, runs the validator, and returns a scorecard with a recommended status and priority.
- A security review of the web-ingestion path, focused on prompt injection from fetched
  pages.
- Update `docs/agent/agents.md` and `docs/agent/skills.md`.

**Success criteria:** `/source-research ieee-spectrum` produces or updates a note that
passes the validator. Every factual field is cited or marked `(unverified)`. The agent
definition's write scope and no-auth/no-CAPTCHA rules are covered by the security review.

---

### Task 03.0 - Read-only LangRank MCP Server

**Goal:** expose the local LangRank database to any MCP-capable agent (Claude Code, the
source researcher, IDE assistants) as a set of read-only tools. Research can then ask "what
do we already have for Kotlin?", "where are the gaps in RedMonk history?", or "does this
candidate source's 2024 top-10 disagree sharply with what we store?" without writing SQL or
shelling out.

- Built on the official Python MCP SDK, `mcp` 2.x. The server class is `MCPServer` from
  `mcp.server`, tools are registered with `@server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))`,
  and the server runs over stdio. It ships as an optional extra `langrank[mcp]`, so the core
  CLI gains no new runtime dependency.
- New CLI command `langrank mcp serve`. It imports the extra lazily and raises a
  `ConfigurationError` with an install hint when the extra is missing.
- Tools:
  - `list_ratings`
  - `list_metrics`
  - `query_observations` (row limit, default 500, hard maximum 5000)
  - `coverage`
  - `provider_status`
  - `methodology_notes`
  - `resolve_language`
  - `compare_normalized`: optional, registered only when
    [Milestone 0002 Task 01.0](/docs/roadmap/0002-cross-rating-analysis/plan.md#task-010---cross-rating-normalization--comparison)
    has landed.
- Resources: `langrank://source-notes/{source_id}`, which serves the Task 01.0 notes.
- Read-only by construction: the database is opened through
  `sqlite3.connect("file:...?mode=ro", uri=True)` and never migrated or seeded. There are no
  fetch, import, or network tools.
- Every observation row returned carries its provenance fields (`source_url`,
  `parser_version`, `is_derived`, `derivation_method`, `retrieved_at`). Every
  multi-rating response carries a `caveat` field stating that raw values are not comparable
  across ratings.
- A threat model in `docs/security/`, registration in `.mcp.json`, and usage docs.

**Success criteria:** the in-memory `mcp.Client` tests exercise every tool. A write attempt
through the server's connection raises `sqlite3.OperationalError`. `langrank mcp serve`
without the extra exits with code 2 and prints the install hint. The threat model has no
open CRITICAL findings.

---

### Task 04.0 - Provider Intake Scaffold

**Goal:** remove the boilerplate between "this source is vetted" and "a provider task is
ready to implement", while keeping every generated file an obvious stub.

- `scripts/scaffold_provider.py <source-id> --milestone NNNN [--task TT.t]` reads a
  validated source note and generates:
  - `src/langrank/providers/<module>.py`, a skeleton modeled on
    `src/langrank/providers/demo.py`, with `NotImplementedError` in `fetch`/`parse`;
  - `tests/fixtures/<provider-id>/.gitkeep`;
  - `tests/contract/test_<module>_provider.py`, skipped until implemented;
  - a printed `ProviderRegistry` / `normalization/languages.py` hint;
  - a roadmap task folder stub from
    [docs/roadmap/_templates/](/docs/roadmap/_templates/task-readme.md).
- Idempotent and never overwrites. Files that already exist are reported and skipped.
  `--dry-run` lists the plan without writing anything.
- `/provider-scaffold <source-id>` skill wraps the script and refuses to run unless the note's
  `status` is `planned` and `terms_url`/`automation` are filled in.

**Success criteria:** running the script twice yields an identical tree and a second run
that reports only "skipped". The generated skeleton passes `ruff` and `mypy`, and its
contract test is collected and skipped.

---

### Task 05.0 - Source Watch Loop

**Goal:** notice when a tracked source has probably published a new edition, and give a
human a drafted note update and an optional GitHub issue. It never fetches into the
database.

- `scripts/source_calendar.py` computes which sources are *due* from each note's front
  matter: `typical_publication_month`, `cadence`, `last_verified`, and the latest local
  period when a DB path is given. It prints JSON.
- `.claude/loops/source-watch.md`, self-paced through `/loop source-watch` and
  schedulable through `/schedule`. For each due source it:
  1. runs a cheap check: Milestone 0004 freshness when available, otherwise a
     source-researcher check of the edition page;
  2. drafts a note update on a branch;
  3. optionally files or updates a de-duplicated GitHub issue labeled `source-watch`,
     through the already-configured `github` MCP server.
- Every lifecycle transition (`due → checked → {new-edition | unchanged | error}`) ends at a
  human-visible artifact. Errors are reported and never swallowed.

**Success criteria:** with a fixture set of notes and a frozen "today", `source_calendar.py`
selects exactly the expected due sources. A dry run of the loop produces issue drafts
without calling GitHub. Running the loop twice on the same day files no duplicate issues.

---

## Milestone exit criteria

- Every source note in `docs/source-notes/` passes `scripts/check_source_notes.py --check`
  in CI, and `docs/research/source-candidates.md` is up to date.
- `/source-research` can add a new candidate note end to end.
- `langrank mcp serve` exposes the read-only tool set to Claude Code through `.mcp.json`.
- `/provider-scaffold` can turn a `planned` note into a skeleton and a roadmap stub.
- `/loop source-watch` produces human-reviewable drafts.
- None of these paths can write to the LangRank database or bypass the provider
  source-policy gate.

A tool in this milestone that produces a number or a claim without a traceable source is not
done. The project's provenance invariant (see [CLAUDE.md](/CLAUDE.md)) applies to research
output too.
