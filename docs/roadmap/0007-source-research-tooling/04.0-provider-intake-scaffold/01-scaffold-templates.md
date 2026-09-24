# Subtask 04.0/01 - Scaffold Templates

**Task:** [04.0 - Provider Intake Scaffold](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/README.md) ·
**Role:** Python Expert · **Depends on:** Task 01.0 · **Status:** ⬜ Not started

## Goal

Create the `string.Template` files that the scaffold renders. The skeleton must reproduce
the structure of `DemoProvider`, with inert method bodies.

## Baseline

- `src/langrank/providers/demo.py` supplies the method set, imports, and the
  `ProviderMetadata`/`MetricDefinition` shape.

## Files

| Action | Path                                                        | Purpose |
|--------|-------------------------------------------------------------|---------|
| Create | `scripts/templates/provider/provider.py.tmpl`               | Provider skeleton |
| Create | `scripts/templates/provider/contract_test.py.tmpl`          | Skipped contract test |
| Create | `scripts/templates/provider/registry_hint.txt.tmpl`         | Printed registry/alias hint |

## Symbols / fields

Template placeholders:

| Placeholder        | Source |
|--------------------|--------|
| `$provider_id`     | note `provider_id`, or `source_id` when null |
| `$class_name`      | PascalCase of `provider_id` + `Provider`, e.g. `IeeeSpectrumProvider` |
| `$module_name`     | snake_case of `provider_id`, e.g. `ieee_spectrum` |
| `$display_name`    | note `display_name` |
| `$homepage`        | note `homepage` |
| `$granularity`     | `Granularity.MONTH` for `month`, `Granularity.YEAR` otherwise, with a `# TODO` comment when the note says `snapshot`/`quarter`/`half-year` |
| `$measures`        | note `measures` |
| `$note_path`       | `docs/source-notes/<source_id>.md` |

The skeleton contains:

- a class with `provider_id = "$provider_id"`;
- a `metadata()` method that returns real metadata from the note, with `parser_version="$provider_id-v0"` and `metrics=[]` plus a TODO;
- `fetch`/`parse`/`normalize`/`validate` methods that raise `NotImplementedError("see $note_path")`;
- a module docstring stating what the source `measures` and that the source must pass the Milestone 0001 source-policy gate before `fetch()` makes network calls.

## Behaviour & validators

1. The rendered skeleton passes `ruff check`, `ruff format --check` and `mypy`. This is
   verified in subtask 05 by rendering into `tmp_path` and running the tools.
2. The contract-test template marks the whole module
   `pytest.mark.skip(reason="scaffolded: implement $class_name first")`, so a fresh scaffold
   never breaks CI.

## Tests

Covered in [subtask 05](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/05-scaffold-tests.md).

## Success criteria

- [ ] The three template files exist, and every placeholder above is used at least once.

## Constraints

- The skeleton never performs I/O at import time, and has no network or DB access
  ([CLAUDE.md](/CLAUDE.md) provider rules).

## Out of scope

- Rendering logic: [subtask 02](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/02-scaffold-script.md).
