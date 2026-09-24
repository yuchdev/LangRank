# Subtask 03.0/02 - Read-only Database Mode

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Let `Database` be opened read-only: no migration, no seeding, and SQLite `mode=ro`. Add the
one provenance-carrying read query the MCP tools need. Make `AppState.database` lazy, so a
command that never touches the read-write database never creates or migrates it.

## Baseline

- `Database.__init__(self, db_path)` creates the parent dir, then `migrate()`s and
  `seed_languages()`.
- `Database.connect()` uses `sqlite3.connect(self.db_path)`.
- `cli.py:AppState.__init__` sets `self.database = Database(config.db_path)` eagerly.
- `db/migrations.py:SCHEMA_VERSION = 2`.
- `errors.py:StorageError` exists.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/db/repository.py`        | `read_only` flag, `ObservationRow`, `query_observations()` |
| Modify | `src/langrank/cli.py`                  | `AppState.database` becomes a `functools.cached_property` |
| Create | `tests/unit/test_database_read_only.py`| Tests |

## Symbols / fields

| Symbol                              | Kind      | Type / signature                                                                  | Default | Notes |
|-------------------------------------|-----------|-----------------------------------------------------------------------------------|---------|-------|
| `Database.__init__`                 | method    | `(db_path: Path, *, read_only: bool = False) -> None`                             | `False` | `read_only=True`: no mkdir, no migrate, no seed |
| `Database.read_only`                | attribute | `bool`                                                                            | -       | |
| `Database.connect`                  | method    | unchanged signature                                                               | -       | When read-only: `sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)`; `PRAGMA foreign_keys = ON` is harmless on a read-only connection and stays |
| `ObservationRow`                    | dataclass | frozen; fields per the ADR's `ObservationRow`                                     | -       | |
| `Database.query_observations`       | method    | `(filters: QueryFilters, *, limit: int) -> tuple[list[ObservationRow], int]`      | -       | Returns (rows ≤ limit, total count); parameterized SQL only |
| `AppState.database`                 | property  | `functools.cached_property -> Database`                                           | -       | Existing callers unchanged |

## Behaviour & validators

1. `Database(path, read_only=True)` raises `StorageError("Database not found: <path>. Run `langrank fetch` first.")`
   if the path does not exist. It never creates the file.
2. `Database(path, read_only=True)` raises `StorageError` if
   `schema_version() < SCHEMA_VERSION`, telling the user to run any read-write command
   once to migrate.
3. On a read-only connection, any `INSERT`/`UPDATE`/`DELETE`/`CREATE` raises
   `sqlite3.OperationalError` ("attempt to write a readonly database").
4. `query_observations` orders by `rating_id, metric_id, language_id, period_start`, and
   applies `LIMIT ?` and a separate `COUNT(*)`. Filters mirror `query_rows`.
5. The default read-write behavior of `Database(path)` is byte-for-byte unchanged, so all
   existing tests pass untouched.

## Tests

| Test function                                         | File                                     | Type        | Asserts |
|-------------------------------------------------------|------------------------------------------|-------------|---------|
| `test_read_only_missing_file_raises_storage_error`    | `tests/unit/test_database_read_only.py`  | Unit        | No file created at the path |
| `test_read_only_rejects_writes`                       | same                                     | Integration | Seeded tmp DB; `connection.execute("INSERT …")` → `sqlite3.OperationalError` |
| `test_read_only_does_not_migrate_or_seed`             | same                                     | Integration | File mtime and `schema_migrations` unchanged after construction |
| `test_read_only_old_schema_raises`                    | same                                     | Integration | DB at schema v1 → `StorageError` |
| `test_query_observations_limit_and_total`             | same                                     | Integration | Demo-seeded DB; `limit=3` → 3 rows, `total` > 3 |
| `test_query_observations_carries_provenance`          | same                                     | Integration | `parser_version`, `retrieved_at`, `is_derived` populated |
| `test_appstate_database_is_lazy`                      | `tests/integration/test_cli.py`          | Integration | Constructing `AppState` does not create the DB file |

## Success criteria

- [ ] All tests above pass. Existing tests are unchanged and green.
- [ ] `grep -n "mode=ro" src/langrank/db/repository.py` matches.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `Database` remains the only module that touches SQL ([CLAUDE.md](/CLAUDE.md) § Storage).
- No migration is added in this subtask.

## Out of scope

- The MCP server itself: [subtask 03](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/03-optional-extra-and-cli-command.md).
