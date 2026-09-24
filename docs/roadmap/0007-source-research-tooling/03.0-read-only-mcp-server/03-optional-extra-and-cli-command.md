# Subtask 03.0/03 - Optional Extra & `mcp serve` Command

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Add the `mcp` optional extra, the `langrank.mcp` package with a `build_server()` factory,
and a `langrank mcp serve` Typer command that runs it over stdio. The `mcp` package is
imported lazily.

## Baseline

- `pyproject.toml` has no `[project.optional-dependencies]` section. Its dependencies are
  `httpx`, `matplotlib`, `rich` and `typer`.
- `cli.py` registers Typer sub-apps with `app.add_typer(...)` (`ratings`, `languages`,
  `export`).
- Output uses a `rich` `Console`, so **stdout must stay clean** under stdio transport: it
  carries the JSON-RPC stream.
- `errors.py:ConfigurationError` exists.
- CI runs `uv sync --frozen`, which installs no extras.

## Files

| Action | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| Modify | `pyproject.toml`                      | `[project.optional-dependencies] mcp = ["mcp>=2.2,<3"]`; mypy override `module = ["mcp.*"]` only if stubs are missing |
| Modify | `uv.lock`                             | `uv lock` |
| Create | `src/langrank/mcp/__init__.py`        | Exports `build_server` lazily (no top-level `import mcp`) |
| Create | `src/langrank/mcp/server.py`          | `build_server(database, registry, notes_dir) -> MCPServer` |
| Modify | `src/langrank/cli.py`                 | `mcp_app = typer.Typer(help="Model Context Protocol server")`; `mcp serve` command |
| Modify | `.github/workflows/ci.yml`            | Add a matrix dimension or extra job running `uv sync --frozen --extra mcp` + pytest |

## Symbols / fields

| Symbol                      | Kind     | Type / signature                                                                                          | Default | Notes |
|-----------------------------|----------|-----------------------------------------------------------------------------------------------------------|---------|-------|
| `SERVER_NAME`               | constant | `str`                                                                                                     | `"langrank"` | |
| `build_server`              | function | `(*, database: Database, registry: ProviderRegistry, notes_dir: Path) -> "MCPServer"`                     | - | `database.read_only` must be `True`, else `ConfigurationError` |
| `require_mcp()`             | function | `() -> None`                                                                                              | - | `importlib.util.find_spec("mcp")` is `None` → `ConfigurationError("The MCP server needs the optional extra: uv sync --extra mcp  (or pip install 'langrank[mcp]')")` |
| `mcp_serve`                 | command  | `langrank mcp serve [--db PATH] [--notes-dir PATH]`                                                       | notes dir `docs/source-notes` relative to CWD if it exists, else resources disabled | |

## Behaviour & validators

1. `mcp serve` builds `Database(config.db_path, read_only=True)` directly, so it never
   touches the lazy read-write `AppState.database` (subtask 02).
2. When the extra is missing, the command prints the `require_mcp` message to **stderr** and
   exits with code 2.
3. Nothing is written to stdout except by the MCP transport. Diagnostics go through
   `Console(stderr=True)`.
4. `server.run()` is called with the default (stdio) transport. No HTTP transport flag is
   exposed.
5. `import langrank.cli` succeeds without the extra installed. Only `mcp serve` triggers the
   import.

## Tests

| Test function                                  | File                                 | Type        | Asserts |
|------------------------------------------------|--------------------------------------|-------------|---------|
| `test_mcp_serve_without_extra_exits_2`         | `tests/integration/test_cli_mcp.py`  | Mock        | Patch `find_spec` → `None`; `CliRunner` exit 2, hint in stderr |
| `test_cli_imports_without_mcp_installed`       | same                                 | Unit        | `sys.modules` has no `mcp` after `import langrank.cli` |
| `test_build_server_rejects_read_write_database`| `tests/unit/test_mcp_server.py`      | Unit        | `importorskip("mcp")`; `Database(tmp, read_only=False)` → `ConfigurationError` |

## Success criteria

- [ ] `uv sync --frozen` (no extra) + `uv run pytest` is green, and MCP tests are skipped.
- [ ] `uv sync --frozen --extra mcp` + `uv run pytest` is green.
- [ ] `uv run langrank mcp serve --help` lists `--db` and `--notes-dir`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` green.

## Constraints

- Run `/dep-audit` for the new extra (license and CVE check). The `dep_audit.py` hook will
  prompt for it.
- The version pin is `mcp>=2.2,<3`. The 2.x API (`MCPServer`) is not source-compatible with
  1.x (`FastMCP`).

## Out of scope

- Tool bodies: [subtask 04](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/04-query-tools.md).
