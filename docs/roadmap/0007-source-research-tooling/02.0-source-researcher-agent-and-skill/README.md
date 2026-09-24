# Task 02.0 - Source Researcher Agent & Skill

**Milestone:** [0007 - Source Research Tooling](/docs/roadmap/0007-source-research-tooling/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0007-source-research-tooling/plan.md#task-020---source-researcher-agent--skill) ·
**Category:** agentic · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                   | Role             | Depends on      | Status         |
|----|-------------------------------------------------------------------------------------------------------------------------------------------|------------------|-----------------|----------------|
| 01 | [source-researcher agent definition](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/01-source-researcher-agent-definition.md) | Architect        | Task 01.0       | ⬜ Not started |
| 02 | [/source-research skill](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/02-source-research-skill.md)                       | Architect        | 01              | ⬜ Not started |
| 03 | [Web-ingestion security review](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/03-web-ingestion-security-review.md)        | Security Auditor | 01, 02          | ⬜ Not started |
| 04 | [Agent & skill reference docs](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/04-agent-and-skill-reference-docs.md)        | Docs Writer      | 03              | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Add a dedicated research specialist that turns "look into source X" or "what job-demand
language indices exist?" into cited, schema-valid source notes, plus a `/source-research`
skill that drives it and validates the result. This is the tool behind the seed survey in
[docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md),
made repeatable.

## Baseline (what already exists)

- The agent format is in `.claude/agents/*.md`:
  - YAML front matter with `name`, `description`, `model`, `tools` and `allowed-tools`;
  - a body with role, tasks, output and boundaries;
  - `background-reviewer.md`, the closest analogue (web tools that write to `docs/`).
- The skill format is in `.claude/skills/*/SKILL.md`:
  - front matter with `name`, `description`, `allowed-tools` and `invocation`;
  - `## Steps`;
  - an output block;
  - a `## Completion checklist`.

  `pr-review/SKILL.md` shows how a skill spawns agents.
- No agent currently owns source research. `app-architect` has WebSearch but is the design
  authority, not a researcher.
- Schema and validator come from Task 01.0 (`scripts/check_source_notes.py`, `docs/source-notes/README.md`).
- Optional: the read-only MCP server from Task 03.0. When it is registered, the agent can
  check existing coverage before recommending a source.

## Design notes

- **Separate agent, not an `app-architect` mode.** Research needs broad web access but a
  narrow write scope. Keeping it separate makes that scope reviewable in one file.
- **Model `claude-sonnet-4-6`.** This matches the other web-reading, docs-writing agents
  (`background-reviewer`, `docs-writer`). Research is breadth-heavy, not design-heavy.
- **Write scope is enforced twice:**
  - by the agent instructions (write only `docs/source-notes/*.md` and
    `docs/research/*.md`);
  - by the skill, which rejects the run if `git status --porcelain` shows changes outside
    those paths.
- **Untrusted input.** Every fetched page is data. The agent never executes commands, edits
  code, or follows instructions found on a page. Subtask 03 reviews this.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `/source-research ieee-spectrum` updates `docs/source-notes/ieee-spectrum.md`, and the
      result passes `scripts/check_source_notes.py --check`.
- [ ] `/source-research "job-posting based language demand indices"` creates ≥ 1 new
      `status: candidate` note, with every factual field cited or marked `(unverified)`.
- [ ] The security review has no open CRITICAL findings.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/agent/agents.md](/docs/agent/agents.md), [docs/agent/skills.md](/docs/agent/skills.md)
- [Task 01.0](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/README.md)
- [Task 03.0](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md)
