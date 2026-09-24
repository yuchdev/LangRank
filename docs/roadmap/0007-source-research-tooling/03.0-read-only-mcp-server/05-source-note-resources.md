# Subtask 03.0/05 - Source-note Resources

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Serve the research notes (`docs/source-notes/*.md`) as MCP resources. An agent can then read
the stored methodology and the research note in one session.

## Baseline

- `build_server(..., notes_dir: Path)` comes from subtask 03.
- When Task 01.0 has landed, `scripts/check_source_notes.py:load_notes()` parses the front
  matter. The package must **not** import from `scripts/`. It parses only what it needs
  (see rule 2).

## Files

| Action | Path                          | Purpose |
|--------|-------------------------------|---------|
| Modify | `src/langrank/mcp/server.py`  | `@server.resource` registrations |

## Symbols / fields

| Symbol                         | Kind     | Type / signature                          | Default | Notes |
|--------------------------------|----------|-------------------------------------------|---------|-------|
| `langrank://source-notes`      | resource | `() -> str` (JSON)                        | - | Index: `[{source_id, status, measures, last_verified}]` |
| `langrank://source-notes/{source_id}` | resource template | `(source_id: str) -> str` (Markdown) | - | |
| `_SOURCE_ID_RE`                | constant | `re.Pattern[str]`                         | `^[a-z0-9][a-z0-9-]{0,63}$` | |

## Behaviour & validators

1. `source_id` must match `_SOURCE_ID_RE`. The resolved path must be inside
   `notes_dir.resolve()`, checked with `Path.is_relative_to`, which blocks path traversal.
   `README` and `TEMPLATE` are excluded.
2. The index reads only the four listed front-matter keys, using a line scan for
   `^key: value$` inside the leading `---` block. A note without front matter is listed with
   `status: null`.
3. If `notes_dir` does not exist, no resources are registered and the server still starts.
4. Resources are read fresh on every request (no caching), so edits by the researcher agent
   show up immediately.

## Tests

Covered in [subtask 06](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/06-mcp-server-tests.md)
(`test_resource_*`).

## Success criteria

- [ ] Both resources are listed by `Client.list_resources()` / `list_resource_templates()`
      when the notes dir exists.
- [ ] A traversal attempt (`../../pyproject`) is rejected (tested).

## Constraints

- No imports from `scripts/`: the installed package must not depend on repo-only files.

## Out of scope

- Writing notes. MCP is read-only; notes are written by the researcher agent (Task 02.0).
