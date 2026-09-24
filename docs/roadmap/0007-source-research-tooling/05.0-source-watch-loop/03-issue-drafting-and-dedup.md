# Subtask 05.0/03 - Issue Drafting & De-duplication

**Task:** [05.0 - Source Watch Loop](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Render issue drafts deterministically, and de-duplicate them so repeated loop runs never
file the same issue twice. Filing itself goes through the existing `github` MCP server,
and only when the loop is not in `--dry-run` or `--no-issues` mode.

## Baseline

- The `github` MCP server's tools `mcp__github__search_issues`, `create_issue` and
  `add_issue_comment` are audited by `.claude/hooks/github_audit.py`.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `scripts/source_watch_issue.py`              | Render title/body/marker for a (source, state, run date) |
| Create | `tests/scripts/test_source_watch_issue.py`   | Tests |
| Modify | `.claude/loops/source-watch.md`              | Step 3 calls the renderer, then search → create-or-comment |

## Symbols / fields

| Symbol              | Kind      | Type / signature                                                                | Default | Notes |
|---------------------|-----------|---------------------------------------------------------------------------------|---------|-------|
| `LABEL`             | constant  | `str`                                                                           | `"source-watch"` | |
| `IssueDraft`        | dataclass | frozen; `title: str`, `body: str`, `marker: str`, `labels: tuple[str, ...]`    | - | |
| `marker_for()`      | function  | `(source_id: str, state: str, edition_key: str) -> str`                         | - | `<!-- source-watch:<source_id>:<state>:<edition_key> -->` |
| `render_issue()`    | function  | `(source_id: str, state: str, *, edition_key: str, note_path: str, details: str, branch: str \| None) -> IssueDraft` | - | Pure |
| `main()`            | function  | `(argv: list[str] \| None = None) -> int`                                       | - | Prints the draft as JSON |

## Behaviour & validators

1. `edition_key` is `YYYY` for annual, `YYYY-MM` for monthly or semiannual windows, and the
   run date for `overdue`/`error`. This makes the key stable across repeated runs within
   one window.
2. Title format: `[source-watch] <display_name>: <state> (<edition_key>)`.
3. The body contains:
   - the marker as its first line;
   - the note link (repo-root absolute path);
   - the `measures` label;
   - the evidence URLs from the researcher's report;
   - the draft branch name;
   - a checklist for the human: verify the edition, merge the note update, and open or
     update a provider task if the methodology changed.
4. De-duplication, done in the loop: search open issues for the exact marker. If one is
   found, add a comment only if `details` changed. Otherwise create the issue with `LABEL`.
5. `details` is truncated to 4000 characters, and any text resembling secrets is redacted by
   the existing `secret_scan` hook pattern set before rendering.

## Tests

| Test function                            | File                                        | Type | Asserts |
|------------------------------------------|---------------------------------------------|------|---------|
| `test_marker_stable_within_window`       | `tests/scripts/test_source_watch_issue.py`  | Unit | Same inputs → same marker |
| `test_marker_differs_per_edition`        | same                                        | Unit | 2026 vs 2027 |
| `test_render_issue_body_contains_marker_first` | same                                  | Unit | |
| `test_details_truncated`                 | same                                        | Unit | 10k chars → ≤ 4000 + ellipsis |
| `test_main_prints_json`                  | same                                        | Unit | Valid JSON with 4 keys |

## Success criteria

- [ ] All tests pass. The script is stdlib-only.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- The script itself never talks to GitHub. Only the loop does, through the audited MCP tools.

## Out of scope

- Scheduling: [subtask 04](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/04-scheduling-and-lifecycle-review.md).
