# Task 04.0 - Provider Intake Scaffold

**Milestone:** [0007 - Source Research Tooling](/docs/roadmap/0007-source-research-tooling/plan.md) ·
**Spec source:** [plan.md § Task 04.0](/docs/roadmap/0007-source-research-tooling/plan.md#task-040---provider-intake-scaffold) ·
**Category:** agentic · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                         | Role           | Depends on | Status         |
|----|---------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Scaffold templates](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/01-scaffold-templates.md)            | Python Expert  | Task 01.0  | ⬜ Not started |
| 02 | [Scaffold script](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/02-scaffold-script.md)                  | Python Expert  | 01         | ⬜ Not started |
| 03 | [Roadmap task stub generation](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/03-roadmap-task-stub-generation.md) | Python Expert | 02    | ⬜ Not started |
| 04 | [/provider-scaffold skill](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/04-provider-scaffold-skill.md) | Architect      | 03         | ⬜ Not started |
| 05 | [Scaffold tests](/docs/roadmap/0007-source-research-tooling/04.0-provider-intake-scaffold/05-scaffold-tests.md)                    | Testing Expert | 03         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Turn a vetted (`status: planned`) source note into the standard starting kit for a new
provider:

- a provider skeleton modeled on `providers/demo.py`;
- a fixture directory;
- a skipped contract-test stub;
- registry and alias hints;
- a roadmap task folder stub that follows `docs/roadmap/_templates/`.

It is deterministic and idempotent, and it never overwrites. The generated code is
deliberately inert: it raises `NotImplementedError` until a human or `python-expert`
implements it.

## Baseline (what already exists)

- `src/langrank/providers/demo.py:DemoProvider` is the reference implementation. It has a
  `provider_id` class attribute, `__init__(cache_dir)`, and the methods
  `metadata()`/`fetch()`/`parse()`/`normalize()`/`validate()`, plus
  `upstream_latest_period()`.
- `src/langrank/providers/registry.py:ProviderRegistry.__init__` is a hand-written dict. The
  scaffold **prints** the line to add and never edits it automatically.
- `src/langrank/normalization/languages.py:LanguageNormalizer` holds hard-coded
  `CanonicalLanguage` entries. The scaffold prints alias hints taken from the note's
  `## Language naming quirks` section.
- `tests/contract/test_production_providers.py` shows the contract-test style.
  `tests/fixtures/<provider>/sample.csv` is the fixture layout.
- The templates are `docs/roadmap/_templates/task-readme.md` and `subtask.md`.
- Task 01.0 provides `load_notes()` and `SourceNote`.

## Design notes

- **Templates are files, rendered with `string.Template`.** They are stdlib-only and use
  `$placeholder` syntax, so they cannot collide with Python braces. They live under
  `scripts/templates/provider/`.
- **Never edit existing files.** Registry and normalizer changes are printed as hints. Those
  files carry the project's key invariants (hand-registered providers, canonical language
  list), so a human makes those edits.
- **Gate on the note.** The note must be `planned`, have `terms_url` set, and have
  `automation` other than `unknown`. That is the Milestone 0001 source-policy gate, recorded
  before any code exists.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `python scripts/scaffold_provider.py ieee-spectrum --milestone 0001 --task 03.0 --dry-run`
      lists the planned files without writing.
- [ ] Two consecutive real runs give an identical tree. The second run reports only `skipped`.
- [ ] The generated skeleton passes `ruff` and `mypy`. Its contract test is collected and skipped.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/providers.md](/docs/providers.md)
- [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md)
- [docs/roadmap/README.md](/docs/roadmap/README.md) - hierarchy and naming convention
