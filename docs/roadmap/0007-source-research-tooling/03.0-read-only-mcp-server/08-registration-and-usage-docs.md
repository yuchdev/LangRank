# Subtask 03.0/08 - Registration & Usage Docs

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Docs Writer · **Depends on:** 06, 07 · **Status:** ⬜ Not started

## Goal

Register the server for Claude Code in `.mcp.json`, grant the researcher agent its tools,
and document how agents use the server during source research.

## Baseline

- `.mcp.json` registers `github` (npx, `${GITHUB_PERSONAL_ACCESS_TOKEN}`) and `playwright`.
- `.claude/agents/source-researcher.md` (Task 02.0/01) lists `mcp__langrank__*` as optional.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `.mcp.json`                            | Add `"langrank": {"command": "uv", "args": ["run", "--extra", "mcp", "langrank", "mcp", "serve"]}` |
| Create | `docs/agent/mcp.md`                    | MCP servers reference: `github`, `playwright`, `langrank` — what each is for, which agents use it |
| Modify | `docs/README.md`                       | Registry entry for `docs/agent/mcp.md` |
| Modify | `.claude/agents/source-researcher.md`  | Promote the `mcp__langrank__*` tools from optional to listed, if Task 02.0 has landed |
| Modify | `README.md`                            | Short "Use from an AI agent (MCP)" section with the install and `.mcp.json` snippet |

## Symbols / fields

| Symbol                      | Kind         | Notes |
|-----------------------------|--------------|-------|
| `mcpServers.langrank`       | `.mcp.json`  | No env secrets required; honors `LANGRANK_DB` |
| "Research recipes"          | heading      | In `docs/agent/mcp.md` |

## Behaviour & validators

1. The "Research recipes" section has the four worked examples from the Task README goal:
   - coverage gap;
   - overlap check;
   - rank-order sanity comparison, never raw cross-rating values;
   - naming quirk.

   Each shows the tool calls and the caveat handling.
2. The docs state plainly that the server is read-only and cannot fetch.

## Tests

Manual smoke check, recorded in the PR:

| Check | Expected |
|-------|----------|
| In Claude Code: `/mcp` | `langrank` connected; 7 tools listed |
| Ask "what ratings cover rust?" | Agent calls `coverage` with `language="rust"` |

## Success criteria

- [ ] `.mcp.json` is valid JSON with three servers (`python -m json.tool .mcp.json`).
- [ ] `python3 scripts/check_doc_links.py docs/agent docs/README.md README.md` exits 0.

## Constraints

- No secrets in `.mcp.json`. The `secret_scan` hook enforces this.

## Out of scope

- Publishing to an MCP registry or distributing to other hosts.
