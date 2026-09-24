# Subtask 02.0/04 - Agent & Skill Reference Docs

**Task:** [02.0 - Source Researcher Agent & Skill](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/README.md) ·
**Role:** Docs Writer · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Register the new agent and skill in the fleet reference docs, and add a short research
workflow section to the agent tutorial.

## Baseline

- `docs/agent/agents.md` has one `| Agent | Model | Description |` table row per agent.
- `docs/agent/skills.md` has one `| Skill | Invocation | Description |` row per skill.
- `docs/agent/tutorial.md` is the fleet walkthrough.

## Files

| Action | Path                      | Purpose |
|--------|---------------------------|---------|
| Modify | `docs/agent/agents.md`    | Add a `source-researcher` row, alphabetical, matching the front-matter `description` verbatim |
| Modify | `docs/agent/skills.md`    | Add a `source-research` row |
| Modify | `docs/agent/tutorial.md`  | Add a "Researching a new ranking source" section: `/source-research` → review note → `/provider-scaffold` (Task 04.0) → provider task |

## Symbols / fields

| Symbol                                   | Kind    | Notes |
|------------------------------------------|---------|-------|
| `source-researcher` row                  | table   | Model `claude-sonnet-4-6` |
| `source-research` row                    | table   | Invocation from the skill's front matter |
| "Researching a new ranking source"       | heading | New `##` section in tutorial.md |

## Behaviour & validators

1. The description cells are copied verbatim from front matter, so the docs don't drift
   from the agent/skill files.

## Tests

None (docs).

## Success criteria

- [ ] `grep -n "source-researcher" docs/agent/agents.md` and `grep -n "source-research" docs/agent/skills.md` each match one table row.
- [ ] `python3 scripts/check_doc_links.py docs/agent` exits 0.

## Constraints

- Links use absolute-from-repo-root paths (per [docs/roadmap/README.md](/docs/roadmap/README.md)).

## Out of scope

- MCP usage docs: [Task 03.0/08](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/08-registration-and-usage-docs.md).
