# Subtask 02.0/10 - Provider documentation

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Docs Writer · **Depends on:** 09 · **Status:** ⬜ Not started

## Goal

User docs for `github`: variants, derived-value semantics, and why it is not RedMonk.

## Baseline

`docs/providers.md`; `docs/source-notes/github.md` (subtask 01).

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `docs/providers.md` | `## GitHub provider` section |
| Modify | `README.md` | Provider list |
| Modify | `docs/data-model.md` | Document `Granularity.QUARTER` and `YYYY-Qn` labels |

## Symbols / fields

Section contains: metric table (4 IDs, derived?), `--source` values and `auto` default,
suppression caveat, commit pinning, Octoverse basis table, example
`langrank plot --rating github --metric github-innovation-graph-share --languages python,typescript,rust --years 5`.

## Behaviour & validators

1. States that `fetch all` only fetches Innovation Graph.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | Link check introduces no new problems |

## Success criteria

- [ ] All items present; link check clean.

## Constraints

- Absolute-from-root links.

## Out of scope

- Comparison with RedMonk series (Milestone 0002).
