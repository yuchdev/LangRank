# Subtask 03.0/06 - MCP Server Tests

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Testing Expert · **Depends on:** 04, 05 · **Status:** ⬜ Not started

## Goal

Test every tool and resource end to end through the SDK's in-memory client. The tests must
skip cleanly when the `mcp` extra is not installed.

## Baseline

- The SDK testing pattern (mcp 2.x) looks like this:
  ```python
  from mcp import Client

  async with Client(server, raise_exceptions=True) as c:
      result = await c.call_tool("name", {...})
  ```
  Results expose `structured_content`, `content` and `is_error`. Tests run under anyio via
  `@pytest.mark.anyio`, with an `anyio_backend` fixture returning `"asyncio"`. `anyio` is an
  `mcp` dependency.
- `pytest-asyncio` is already in the dev group. Use the anyio marker only, to avoid
  double-running.
- `tests/conftest.py` and the demo provider give a deterministic, network-free dataset.

## Files

| Action | Path                              | Purpose |
|--------|-----------------------------------|---------|
| Create | `tests/unit/test_mcp_server.py`   | In-memory client tests |
| Modify | `tests/conftest.py`               | `demo_db_read_only` fixture: fetch `demo` into a tmp DB through `FetchService`, then reopen with `read_only=True` |

## Symbols / fields

| Symbol                 | Kind    | Notes |
|------------------------|---------|-------|
| `pytestmark`           | module  | `pytest.importorskip("mcp")` at top of module |
| `anyio_backend`        | fixture | returns `"asyncio"` |
| `mcp_client`           | fixture | `async with Client(build_server(...), raise_exceptions=True) as c: yield c` |

## Behaviour & validators

1. No network: tests use only the `demo` provider and fixture notes under
   `tests/fixtures/source-notes/valid/` (Task 01.0/02).

## Tests

| Test function                                    | File                             | Type        | Asserts |
|--------------------------------------------------|----------------------------------|-------------|---------|
| `test_list_tools_are_all_read_only`              | `tests/unit/test_mcp_server.py`  | Integration | Every tool's `annotations.read_only_hint is True` and `open_world_hint is False` |
| `test_list_ratings_includes_demo`                | same                             | Integration | `demo` present |
| `test_list_metrics_unknown_rating_is_error`      | same                             | Integration | `is_error` true, no traceback text |
| `test_query_observations_has_provenance`         | same                             | Integration | Every row has `parser_version`, `retrieved_at`, `is_derived` |
| `test_query_observations_limit_truncates`        | same                             | Integration | `limit=2` → 2 rows, `truncated` true, `total` > 2 |
| `test_query_observations_limit_bounds`           | same                             | Integration | `limit=0` and `limit=5001` → error |
| `test_query_observations_unknown_language_suggests` | same                          | Integration | Error text contains a suggestion |
| `test_coverage_carries_caveat`                   | same                             | Integration | `caveat` equals `CROSS_RATING_CAVEAT` |
| `test_resolve_language_alias`                    | same                             | Integration | `"golang"` → `"go"` |
| `test_methodology_notes_for_demo`                | same                             | Integration | Returns the stored notes |
| `test_provider_status_lists_registry`            | same                             | Integration | One entry per registered provider |
| `test_compare_normalized_absent_without_0002`    | same                             | Integration | Not in `list_tools()` unless the dependency exists (skip-marked otherwise) |
| `test_resource_index_lists_fixture_notes`        | same                             | Integration | JSON index keys |
| `test_resource_rejects_path_traversal`           | same                             | Integration | `langrank://source-notes/..%2F..%2Fpyproject` → error |
| `test_server_database_rejects_writes`            | same                             | Integration | `database.connect()` + `INSERT` → `sqlite3.OperationalError` |

## Success criteria

- [ ] All tests pass with `--extra mcp`, and the module is reported as skipped without it.
- [ ] Run `/document-tests tests/unit/test_mcp_server.py`, so each test has a Scenario /
      Boundaries / On-failure docstring.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Tests never hit the network, and never open the user's real DB (always `tmp_path`).

## Out of scope

- Manual Claude Code smoke test: [subtask 08](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/08-registration-and-usage-docs.md).
