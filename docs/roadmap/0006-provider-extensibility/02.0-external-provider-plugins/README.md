# Task 02.0 - External Provider Plugin Loading

**Milestone:** [0006 - Provider Extensibility](/docs/roadmap/0006-provider-extensibility/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-020---external-provider-plugin-loading) ·
**Category:** provider-infra · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                          | Role             | Depends on          | Status         |
|----|----------------------------------------------------------------------------------------------------------------------------------|------------------|---------------------|----------------|
| 01 | [Provider API stability ADR](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/01-provider-api-stability-adr.md) | Architect        | Task 01.0 complete  | ⬜ Not started |
| 02 | [Plugin API version & entry-point discovery](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/02-entry-point-discovery.md) | Python Expert    | 01                  | ⬜ Not started |
| 03 | [Conflict rules, error isolation & opt-out](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/03-conflicts-isolation-opt-out.md) | Python Expert    | 02                  | ⬜ Not started |
| 04 | [Out-of-tree fixture plugin package](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/04-fixture-plugin-package.md) | Testing Expert   | 03                  | ⬜ Not started |
| 05 | [Plugin trust model & security review](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/05-plugin-trust-model.md) | Security Auditor | 02 (review of 03)   | ⬜ Not started |
| 06 | [Plugin author guide](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/06-plugin-author-guide.md) | Docs Writer      | 03, 05              | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

A package installed alongside `langrank` can register a `RatingProvider` through the
`langrank.providers` entry-point group and appear in `ProviderRegistry` - and therefore in
`fetch`, `query`, `status`, `ratings` - with no change to `langrank` core. A broken or hostile
plugin can be disabled, and a broken one never takes the CLI down with it.

## Baseline (what already exists)

- `src/langrank/providers/registry.py:ProviderRegistry.__init__(cache_dir)` builds a literal
  `dict[str, RatingProvider]` of five built-ins; `get()` raises `ProviderError` on unknown IDs;
  `all()` returns values in insertion order.
- `src/langrank/cli.py:AppState.__init__` constructs `ProviderRegistry(config.cache_path)`.
- `src/langrank/config.py:resolve_config` - precedence CLI flag > env (`LANGRANK_DB`,
  `LANGRANK_CACHE`) > TOML > XDG default; `AppConfig` has `db_path`, `cache_path`, `config_path`.
- No entry points, no plugin concept. Python ≥3.12 → `importlib.metadata.entry_points(group=...)`
  is available with no new dependency.
- Prerequisite: [Task 01.0](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md)
  (capabilities + metric kinds + reusable contract helper).

## Design notes

- **Stabilize contracts first** (plan.md § Stabilize contracts): subtask 01 is an ADR that
  enumerates the exact public surface (`models.py` types, `providers/base.py` protocol,
  `providers/common.py` helpers, `errors.py` hierarchy) and a `PLUGIN_API_VERSION`. No loader
  code lands before it is Accepted.
- **Entry-point value is a factory**, not an instance: `mypkg.provider:make_provider` called as
  `factory(cache_dir: Path) -> RatingProvider` - mirroring built-in constructors (`TiobeProvider(cache_dir)`)
  and letting each plugin get its own cache sub-directory.
- **Built-ins always win** an ID conflict; plugin-vs-plugin conflicts keep neither and warn -
  deterministic, and avoids install-order-dependent behaviour.
- **Isolation, not sandboxing.** Load failures (import error, factory exception, protocol
  mismatch, API-version mismatch) become warnings and the plugin is skipped. Plugins still run
  arbitrary code in-process - that is a trust decision documented in subtask 05, not something
  the loader pretends to prevent.
- **Opt-out** via `--no-plugins` global flag, `LANGRANK_NO_PLUGINS=1`, or TOML
  `plugins = false`, following `resolve_config` precedence.
- **Legal gate:** a plugin with default network access is subject to the
  [Milestone 0001 legal/source-policy gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate);
  core cannot enforce it, so the author guide requires plugins to declare it in metadata caveats.

### Open questions

- Allowlist instead of all-installed? **Default:** load all installed plugins, with an optional
  TOML `plugins_allow = ["id", ...]` evaluated in subtask 05's review; implement only if the
  security review requires it.
- Should plugin providers be visible in `doctor`? **Default:** yes - `doctor` lists
  `plugin providers` with distribution name + version, and `skipped plugins` with reasons.

## Task exit criteria

- [ ] Every subtask above is ✅; ADR Accepted.
- [ ] An out-of-tree fixture package registers via `langrank.providers` and appears in
      `ProviderRegistry.all()` and `langrank ratings` with zero core changes (plan.md success criterion).
- [ ] The Task 01.0 contract helper passes against the fixture plugin.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- Python Packaging - [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/).
- [`importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html#entry-points).
- [docs/adr/README.md](/docs/adr/README.md), [docs/security/README.md](/docs/security/README.md).
