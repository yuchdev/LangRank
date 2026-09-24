# Subtask 02.0/03 - Conflict Rules, Error Isolation & Opt-Out

**Task:** [02.0 - External Provider Plugin Loading](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Make plugin loading safe to leave on by default: ID conflicts resolve deterministically, any
plugin failure becomes a visible warning instead of a crash, and users can disable plugins by
flag, env var, or config file.

## Baseline

- `discover_plugins` / `PluginLoadResult` from [subtask 02](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/02-entry-point-discovery.md).
- `src/langrank/config.py:AppConfig`, `resolve_config(cli_db, cli_cache, cli_config)`,
  `load_file_config` (reads `[langrank]` table as `dict[str, str]`).
- `src/langrank/cli.py:main_callback` (global options), `doctor`.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/providers/plugins.py`    | Conflict + failure handling populating `skipped` |
| Modify | `src/langrank/config.py`               | `AppConfig.plugins_enabled`; resolve `--no-plugins` / `LANGRANK_NO_PLUGINS` / TOML `plugins` |
| Modify | `src/langrank/cli.py`                  | `--no-plugins` global option; warnings printed once; `doctor` rows |
| Modify | `tests/unit/test_plugin_discovery.py`  | Failure/conflict tests |
| Modify | `tests/unit/test_config.py`            | Precedence tests |

## Symbols / fields

| Symbol                         | Kind   | Type / signature                                                     | Default | Notes |
|--------------------------------|--------|----------------------------------------------------------------------|---------|-------|
| `AppConfig.plugins_enabled`    | field  | `bool`                                                               | `True`  | |
| `resolve_config(cli_no_plugins=...)` | param | `cli_no_plugins: bool = False`                                  | `False` | Precedence: CLI > `LANGRANK_NO_PLUGINS` (`1/true/yes`) > TOML `plugins = false` > default `True` |
| `main_callback --no-plugins`   | option | `bool`                                                               | `False` | Global flag |
| `SkippedPlugin.reason`         | field  | `str`                                                                | -       | One of the reason codes below, plus detail |

Reason codes (prefix of `reason`): `import_error`, `factory_error`, `not_a_provider`,
`api_version`, `id_mismatch`, `builtin_conflict`, `duplicate_plugin_id`.

## Behaviour & validators

1. **Built-in wins:** a plugin whose ID equals a built-in ID is skipped (`builtin_conflict`).
2. **Plugin vs plugin:** if two entry points share a name, **both** are skipped
   (`duplicate_plugin_id`) - no install-order-dependent winner.
3. **Isolation:** any `Exception` raised while loading the entry point, importing the module,
   or calling the factory is caught (`except Exception`, never bare `except:`) and recorded;
   `KeyboardInterrupt`/`SystemExit` propagate.
4. `not_a_provider`: returned object lacks any `RatingProvider` protocol member (checked via
   explicit attribute list derived from the protocol, since `Protocol` is not `runtime_checkable`
   today - or make it `@runtime_checkable`; decide and note in code).
5. Skipped plugins produce one `rich` warning line each on stderr per invocation, suppressed by `--quiet`.
6. Failures *after* loading (in `fetch`/`parse`/...) are already handled by `FetchService`
   recording a failed fetch run - no extra handling here.
7. `doctor` shows `plugin providers` (`id=dist version`) and `skipped plugins` (`entry_point: reason`).

## Tests

| Test function                                  | File                                   | Type | Asserts |
|------------------------------------------------|----------------------------------------|------|---------|
| `test_builtin_id_conflict_skips_plugin`        | `tests/unit/test_plugin_discovery.py`  | Mock | Plugin `tiobe` skipped with `builtin_conflict`; `get("tiobe")` is built-in |
| `test_duplicate_plugin_ids_skip_both`          | `tests/unit/test_plugin_discovery.py`  | Mock | Two `acme` → neither loaded, two skips |
| `test_import_error_is_isolated`                | `tests/unit/test_plugin_discovery.py`  | Mock | `ep.load()` raises `ImportError` → skipped, registry builds |
| `test_factory_exception_is_isolated`           | `tests/unit/test_plugin_discovery.py`  | Mock | Factory raises `RuntimeError` → `factory_error` |
| `test_non_provider_object_rejected`            | `tests/unit/test_plugin_discovery.py`  | Mock | Factory returns `object()` → `not_a_provider` |
| `test_keyboard_interrupt_propagates`           | `tests/unit/test_plugin_discovery.py`  | Mock | `KeyboardInterrupt` not swallowed |
| `test_no_plugins_precedence`                   | `tests/unit/test_config.py`            | Unit | CLI > env > TOML > default |
| `test_cli_no_plugins_flag_disables_discovery`  | `tests/integration/test_cli.py`        | E2E  | `langrank --no-plugins ratings` with patched entry points lists only built-ins |
| `test_doctor_lists_skipped_plugins`            | `tests/integration/test_cli.py`        | E2E  | `doctor` output contains `skipped plugins` and reason code |

## Success criteria

- [ ] A plugin that raises on import never changes CLI exit code for commands not using it.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Errors surfaced as warnings go through the `rich` console; no new logging framework.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Sandboxing / allowlists (decided by [subtask 05](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/05-plugin-trust-model.md)).
