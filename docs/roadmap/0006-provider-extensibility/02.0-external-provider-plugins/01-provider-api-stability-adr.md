# Subtask 02.0/01 - Provider API Stability ADR

**Task:** [02.0 - External Provider Plugin Loading](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md) ·
**Role:** Architect · **Depends on:** Task 01.0 complete · **Status:** ⬜ Not started

## Goal

Record, as an Accepted ADR, which symbols form the **public provider API** that third-party
plugins may depend on, how it is versioned, and what may change without a version bump. This
executes plan.md's ordering rule: models → provider contracts → error semantics → provider
metadata are stabilized *before* any loader code (subtasks 02-04).

## Baseline

- `docs/adr/` has only the illustrative `0001-config-loading-via-layered-settings.md`
  (to be deleted once a real ADR lands, per [docs/adr/README.md](/docs/adr/README.md)).
- Candidate public surface today: `models.py` (`SourceRecord`, `Observation`,
  `ProviderMetadata`, `MetricDefinition`, `MetricKind`, `ProviderCapabilities`,
  `MethodologyNote`, `FetchRequest`, `RawArtifact`, `ValidationReport`, `Severity`,
  `Granularity`), `providers/base.py` (`RatingProvider`, `FetchPayload`),
  `providers/common.py` (`payload_from_content`, `build_observation`, `build_observation_hash`,
  `derive_value_capabilities`), `errors.py` (`ProviderError`, `FetchError`, `ParseError`,
  `NormalizationError`).
- Open coupling: providers construct `LanguageNormalizer()` directly and call `resolve()`,
  which raises `UnknownLanguageError` - a plugin with new languages cannot extend the canonical
  list today.

## Files

| Action | Path                                           | Purpose |
|--------|------------------------------------------------|---------|
| Create | `docs/adr/{NNNN}-provider-api-stability.md`    | The ADR (next free number; use `/adr-write "Provider API stability"`) |
| Modify | `docs/adr/README.md`                           | Inventory row |
| Create | `src/langrank/providers/api.py`                | Re-export module: the *only* import path plugins are told to use; defines `PLUGIN_API_VERSION` |

## Symbols / fields

| Symbol                         | Kind      | Type / signature  | Default | Notes |
|--------------------------------|-----------|-------------------|---------|-------|
| `PLUGIN_API_VERSION`           | constant  | `tuple[int, int]` | `(1, 0)` | Major = breaking, minor = additive |
| `langrank.providers.api.__all__` | list    | `list[str]`       | -       | Exactly the symbols the ADR lists as public |

## Behaviour & validators

The ADR must decide (each as a numbered decision with rejected alternatives):

1. **Public surface** = `langrank.providers.api.__all__`; everything else is internal.
2. **Versioning rule:** adding an optional field/method/enum member = minor; removing/renaming,
   changing a required field, or changing a return type = major. Plugins declare the major they
   target (subtask 02); loader rejects mismatched majors.
3. **Protocol return types:** whether `parse()`/`normalize()` stay `list[...]` or become
   `Iterable[...]`. Recommended: **stay `list`** for API v1 (all current callers and `validate()`
   need the full sequence for duplicate checks), and add streaming as an *internal* optimisation
   in [Task 03.0](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/README.md) -
   revisit only if the benchmark budget cannot be met.
4. **Language normalization for plugins:** plugins either map to existing canonical languages or
   raise `UnknownLanguageError`; a plugin-contributed alias/language hook is explicitly deferred
   (records the gap rather than designing it now).
5. **Error semantics:** plugins raise only `ProviderError` subclasses from `errors.py`; any other
   exception from a plugin method is treated by `FetchService` as a failed fetch run (already true)
   and by the loader as a load failure.
6. **Invariants plugins inherit:** no DB access, no network outside `fetch()`, provenance fields
   populated, derived values flagged ([CLAUDE.md](/CLAUDE.md) § Conventions) - documented as
   contract, verified by the Task 01.0 contract helper where mechanically checkable.

## Tests

| Test function                                  | File                                   | Type | Asserts |
|------------------------------------------------|----------------------------------------|------|---------|
| `test_api_module_exports_match_adr`            | `tests/unit/test_provider_api.py`      | Unit | `set(api.__all__)` equals the ADR's frozen list (literal copy in test) - any change forces an ADR edit |
| `test_plugin_api_version_is_semver_tuple`      | `tests/unit/test_provider_api.py`      | Unit | `PLUGIN_API_VERSION == (1, 0)` |

## Success criteria

- [ ] ADR status **Accepted**, with Context / Decision / Consequences per `docs/adr/template.md`.
- [ ] `langrank.providers.api` exists and every name in `__all__` imports.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No loader or entry-point code in this subtask.
- `api.py` only re-exports; it contains no logic besides the constant.

## Out of scope

- Discovery/loading - [subtask 02](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/02-entry-point-discovery.md).
- Security trust model - [subtask 05](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/05-plugin-trust-model.md).
