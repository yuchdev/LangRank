# Subtask {TT.t}/{NN} - {Subtask Title}

**Task:** [{TT.t} - {Task Name}](/docs/roadmap/{NNNN}-{milestone-slug}/{TT.t}-{task-slug}/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

> Template - copy to `docs/roadmap/{NNNN}-{milestone-slug}/{TT.t}-{task-slug}/{NN}-{slug}.md`.
> The section names below are the ones the `subtask-verifier` agent maps to its compliance
> matrix (Files, Symbols / fields, Validators, Tests, Success criteria, Constraints). Keep
> every row concrete enough to be checked with `grep` - exact paths, symbol names, test names.

## Goal

1-3 sentences: the single, atomic outcome of this subtask.

## Baseline

What exists today that this subtask touches (`path:Symbol`), so the implementer does not
rebuild it.

## Files

| Action | Path                                  | Purpose                       |
|--------|---------------------------------------|-------------------------------|
| Create | `src/langrank/...`                    | ...                           |
| Modify | `src/langrank/...`                    | ...                           |
| Create | `tests/unit/test_....py`              | ...                           |

## Symbols / fields

| Symbol           | Kind      | Type / signature                  | Default | Notes |
|------------------|-----------|-----------------------------------|---------|-------|
| `Foo.bar`        | field     | `int \| None`                      | `None`  | ...   |
| `baz()`          | function  | `(x: str) -> list[Observation]`   | -       | ...   |

## Behaviour & validators

Numbered rules. Each rule is either enforced by code (name the function/validation code,
e.g. `ValidationReport` code `rank_positive`) or by a test in the table below.

1. ...

## Tests

| Test function                | File                         | Type        | Asserts |
|------------------------------|------------------------------|-------------|---------|
| `test_...`                   | `tests/unit/test_....py`     | Unit        | ...     |

Types follow `/document-tests`: Unit · Mock · Integration · E2E. Network is always mocked
or fixture-driven; live calls only under `@pytest.mark.integration`.

## Success criteria

- [ ] ...
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Project invariants from [CLAUDE.md](/CLAUDE.md) § "Conventions worth knowing" that apply here
  (providers pure outside `fetch()`, no DB access in providers, no fabricated/interpolated values,
  derived values flagged, append-only migrations, no shared axis across ratings).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- What a reader might expect here but belongs to another subtask (link it).
