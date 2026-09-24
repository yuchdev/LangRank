# Subtask 02.0/06 - Plugin Author Guide

**Task:** [02.0 - External Provider Plugin Loading](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md) ·
**Role:** Docs Writer · **Depends on:** 03, 05 · **Status:** ⬜ Not started

## Goal

A self-contained guide that lets a third party write, package, test, and ship a LangRank
provider plugin, using the fixture package from subtask 04 as the worked example.

## Baseline

- [docs/providers.md](/docs/providers.md) - in-tree provider docs.
- `providers/demo.py` - reference implementation ([CLAUDE.md](/CLAUDE.md)).
- ADR from subtask 01, threat model from subtask 05.

## Files

| Action | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| Create | `docs/plugins.md`                     | Author guide |
| Modify | `docs/providers.md`                   | Link to plugins guide; built-in vs plugin section |
| Modify | `docs/README.md`                      | Registry entry |
| Modify | `README.md`                           | One-paragraph "Third-party providers" + `--no-plugins` |

## Symbols / fields

_Docs-only subtask - no code symbols._

## Behaviour & validators

`docs/plugins.md` must contain these sections (checked by heading grep):

1. **Trust model** - summary + link to `docs/security/threat-model-provider-plugins.md`.
2. **Public API** - `langrank.providers.api`, `PLUGIN_API_VERSION`, `LANGRANK_PLUGIN_API`, link to ADR.
3. **Entry point** - exact `pyproject.toml` snippet; factory signature; ID naming regex.
4. **Implementing the protocol** - `metadata`, `capabilities`, `fetch`, `parse`, `normalize`,
   `validate`, `upstream_latest_period`; `MetricKind` choice table.
5. **Provenance & invariants** - no DB, no network outside `fetch()`, flag derived values, never
   fabricate/interpolate, don't mix measures.
6. **Legal/source-policy declaration** - required caveat text when default network access exists.
7. **Testing your plugin** - how to run `assert_provider_contract` (copy or import guidance).
8. **Troubleshooting** - every `SkippedPlugin` reason code with its fix; `doctor`; `--no-plugins`.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| _(link check)_ `python3 scripts/check_doc_links.py docs/plugins.md` | - | - | No dangling links/anchors |
| `test_plugin_guide_snippet_matches_fixture` | `tests/unit/test_docs_snippets.py` | Unit | The `pyproject.toml` entry-point snippet in `docs/plugins.md` matches the fixture package's (prevents doc drift) |

## Success criteria

- [ ] All eight sections present; every reason code from 02.0/03 documented.
- [ ] Link check clean; snippet test passes.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Absolute-from-repo-root links (`/docs/...`), per [docs/roadmap/README.md](/docs/roadmap/README.md).

## Out of scope

- A published cookiecutter/template repository.
