# Subtask 03.0/02 - IEEE language aliases

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 01.0/02 · **Status:** ⬜ Not started

## Goal

Add `ieee-spectrum`-scoped aliases for IEEE's language labels.

## Baseline

`RATING_ALIASES` / `try_resolve(..., rating_id=)` from
[01.0/02](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/02-rating-scoped-aliases.md).

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/normalization/languages.py` | IEEE aliases |
| Modify | `tests/unit/test_normalization.py` | Tests |

## Symbols / fields

| IEEE label | Canonical | Notes |
|------------|-----------|-------|
| `Shell` | `shell` | |
| `Visual Basic` | `visual-basic` | Distinct from `vb.net` |
| `Assembly` | `assembly` | |
| `SQL` | `sql` | IEEE ranks it as a language |
| `HTML`, `Arduino`, `Verilog`, `VHDL` | per catalog decision | Unmapped → warning unless added to catalog |

## Behaviour & validators

1. Every label in `providers/data/ieee_spectrum.csv` either resolves or is listed in
   `IEEE_UNTRACKED_LABELS: frozenset[str]`.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ieee_aliases_resolve` | `tests/unit/test_normalization.py` | Unit | Mapped labels resolve with `rating_id="ieee-spectrum"` |
| `test_ieee_dataset_labels_all_accounted_for` | `tests/unit/test_normalization.py` | Unit | Resolve or in untracked set |

## Success criteria

- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- `vb.net` and `visual-basic` never merged.

## Out of scope

- Global alias changes.
