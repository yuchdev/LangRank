# Subtask 02.0/02 - Plugin API Version & Entry-Point Discovery

**Task:** [02.0 - External Provider Plugin Loading](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

`ProviderRegistry` discovers factories registered under the `langrank.providers` entry-point
group, checks each against `PLUGIN_API_VERSION`, instantiates it with a per-plugin cache
directory, and adds it after the built-ins. Happy path only - conflicts and failure isolation
are [subtask 03](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/03-conflicts-isolation-opt-out.md).

## Baseline

- `src/langrank/providers/registry.py:ProviderRegistry` - hardcoded dict.
- `src/langrank/providers/api.py:PLUGIN_API_VERSION` from subtask 01.

## Files

| Action | Path                                      | Purpose |
|--------|-------------------------------------------|---------|
| Create | `src/langrank/providers/plugins.py`       | Discovery + loading, returns `PluginLoadResult` |
| Modify | `src/langrank/providers/registry.py`      | Accept `load_plugins: bool` and merge discovered providers |
| Create | `tests/unit/test_plugin_discovery.py`     | Discovery tests with monkeypatched `entry_points` |

## Symbols / fields

| Symbol                              | Kind      | Type / signature                                                            | Default | Notes |
|-------------------------------------|-----------|-----------------------------------------------------------------------------|---------|-------|
| `ENTRY_POINT_GROUP`                 | constant  | `str`                                                                       | `"langrank.providers"` | |
| `PluginInfo`                        | dataclass | frozen: `provider_id: str`, `entry_point: str`, `distribution: str \| None`, `version: str \| None` | - | For `doctor` |
| `SkippedPlugin`                     | dataclass | frozen: `entry_point: str`, `reason: str`                                   | -       | Populated in subtask 03 |
| `PluginLoadResult`                  | dataclass | frozen: `providers: dict[str, RatingProvider]`, `loaded: list[PluginInfo]`, `skipped: list[SkippedPlugin]` | - | |
| `discover_plugins`                  | function  | `(cache_dir: Path) -> PluginLoadResult`                                      | -       | Uses `importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)` |
| `ProviderRegistry.__init__`         | method    | `(cache_dir: Path, *, load_plugins: bool = True) -> None`                   | `True`  | |
| `ProviderRegistry.plugin_result`    | property  | `-> PluginLoadResult`                                                       | -       | Empty result when plugins disabled |

## Behaviour & validators

1. Entry-point **name** is the provider ID; **value** is `module:factory`.
2. Factory contract: `factory(cache_dir: Path) -> RatingProvider`. It is called with
   `cache_dir / "plugins" / <entry-point name>`.
3. The loaded module must expose `LANGRANK_PLUGIN_API = (major, minor)` (module attribute of the
   factory's module); major must equal `PLUGIN_API_VERSION[0]` and minor ≤ current minor.
4. The returned object's `provider_id` must equal the entry-point name.
5. Built-ins are inserted first; plugins follow in sorted entry-point-name order (deterministic `all()`).
6. Discovery happens once per `ProviderRegistry` construction (i.e. once per CLI invocation).

## Tests

| Test function                                         | File                                   | Type | Asserts |
|-------------------------------------------------------|----------------------------------------|------|---------|
| `test_discovers_plugin_from_entry_point`              | `tests/unit/test_plugin_discovery.py`  | Mock | Monkeypatched `entry_points` returning one `EntryPoint(name="acme", value="tests.unit._acme:make", group=...)` → `registry.get("acme")` works |
| `test_plugin_receives_namespaced_cache_dir`           | `tests/unit/test_plugin_discovery.py`  | Mock | Factory called with `cache_dir/"plugins"/"acme"` |
| `test_plugins_ordered_after_builtins_sorted_by_name`  | `tests/unit/test_plugin_discovery.py`  | Mock | IDs order: 5 built-ins then `a-plugin`, `b-plugin` |
| `test_load_plugins_false_skips_discovery`             | `tests/unit/test_plugin_discovery.py`  | Mock | `entry_points` never called |
| `test_api_major_mismatch_rejected`                    | `tests/unit/test_plugin_discovery.py`  | Mock | `LANGRANK_PLUGIN_API = (2, 0)` → not loaded (lands in `skipped` once subtask 03 exists; here: not in providers) |
| `test_provider_id_must_match_entry_point_name`        | `tests/unit/test_plugin_discovery.py`  | Mock | Mismatch → not loaded |

## Success criteria

- [ ] `grep -n "langrank.providers" src/langrank/providers/plugins.py` finds `ENTRY_POINT_GROUP`.
- [ ] No new runtime dependency in `pyproject.toml`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Providers still never touch the DB; the loader never touches the DB either.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- CLI flags/env, conflict rules, warnings - subtask 03. Real installed package - subtask 04.
