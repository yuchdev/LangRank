# Milestone 0002 - Cross-Rating Analysis

**Package:** `langrank` | **Module root:** `src/langrank/services/`, `src/langrank/cli.py`
**Depends on:** more than one reliable provider history. The existing
bootstrap providers (`tiobe`, `pypl`, `redmonk`, `stackoverflow-survey`)
already qualify, so this milestone does not strictly block on
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) finishing —
but it benefits from the additional histories 0001 adds.

This milestone makes cross-provider comparison possible **without ever
plotting raw values from different ratings on one shared axis** — an
existing project-wide rule (see [CLAUDE.md](/CLAUDE.md)). Rating axes are not
comparable across providers without explicit normalization; every task below
either performs that normalization explicitly or refuses to compare
un-normalized values.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                     | Category | Output                                                       |
|------|---------------------------------------------|----------|---------------------------------------------------------------|
| 01.0 | Cross-Rating Normalization & Comparison      | analysis | `rank_percentile` normalization; `langrank plot compare`       |
| 02.0 | Composite Index                              | analysis | `langrank composite`; explicit sources/weights/normalization, no hidden averaging |
| 03.0 | Snapshot Comparison                          | cli      | `langrank snapshot {year\|latest}`; nearest-observation selection rules |

Task 02.0 depends on Task 01.0 (the composite index consumes the same
normalization methods `plot compare` introduces). Task 03.0 is independent of
01.0/02.0 — it compares raw per-source ranks side by side in a table rather
than combining them onto one axis, so it needs no normalization step.

---

## Shared conventions

### Derived-value labeling

Every value produced by normalization or a composite index must carry
`is_derived=True` and a `derivation_method` (per `models.py`'s `Observation`
provenance fields). No task in this milestone may present a derived value as
raw source data, and normalized values are not persisted unless a clear user
requirement emerges later (compute-on-read by default).

### No hidden averaging / no silent interpolation

A composite or comparison feature must require explicit sources, metric
choice, normalization method, weights, and missing-data handling rather than
defaulting to a silent average (extends the project's existing
no-interpolation rule — see [CLAUDE.md](/CLAUDE.md) — to cross-rating
combination).

### Testing

Each task ships unit tests for its normalization math against known inputs,
and CLI acceptance tests for the new command. `uv run ruff check .`, `uv run
ruff format --check .`, and `uv run mypy src` stay clean throughout.

---

## Per-task specifications

### Task 01.0 - Cross-Rating Normalization & Comparison

**Goal:** make cross-provider comparison possible without ever plotting raw
values from different ratings on one shared axis.

- Only implement once individual provider histories are reliable — a
  judgment call for whoever picks up this task, not a fixed provider-count
  threshold.
- New CLI surface: `langrank plot compare --language python --ratings
  tiobe,pypl,redmonk --years 10`.
- Cross-rating comparison must require or default to explicit normalization.
  First method: `rank_percentile` — for rank `r` among `n` ranked languages,
  `score = 1 - (r - 1) / max(n - 1, 1)`, producing ~1.0 = best, ~0.0 = worst.
  Later methods (`minmax`, `zscore`) are additive, not replacements.
- Every normalized series is visibly labeled as derived; normalized values
  are not persisted unless a clear user requirement emerges later.

**Success criteria:** `plot compare` refuses (or clearly labels) an
unnormalized cross-rating request; `rank_percentile` output is covered by
unit tests against known rank/n inputs.

---

### Task 02.0 - Composite Index

**Goal:** an opt-in, fully-explicit composite score — never a hidden average,
never presented as "the true popularity rating."

- New command: `langrank composite --ratings tiobe,pypl,redmonk,github,
  stackoverflow-survey --normalize rank-percentile --weights 1,1,1,2,2`.
- Required, non-defaulted inputs: included sources, metric choice,
  normalization method, weights, missing-data handling.
- Every result is labeled `derived composite` in output and docs.

**Success criteria:** omitting any required input (sources/metric/
normalization/weights/missing-data policy) is a CLI usage error, not a
silent default; output rows carry the `derived composite` label.

---

### Task 03.0 - Snapshot Comparison

**Goal:** a same-point-in-time cross-source table without silent
interpolation.

- Commands: `langrank snapshot 2020`, `langrank snapshot latest`. Example
  output shape: one row per language, one column per rating
  (TIOBE/PYPL/RedMonk/GitHub/SO Survey rank).
- Define selection rules for the closest observation when a source is
  monthly, snapshot-based, or annual, and show the actual source observation
  date wherever ambiguity matters. Do not interpolate missing cells.

**Success criteria:** a snapshot cell is always either a real observation
(with its true date shown) or explicitly blank — never a computed fill-in.

---

## Milestone exit criteria

`langrank plot compare`, `langrank composite`, and `langrank snapshot` are all
available and every one of their outputs is traceable back to the raw
per-rating observations it was derived from — normalization method, weights,
and selection rules stated explicitly rather than defaulted. This milestone
is not "done" if any comparison feature can produce a number without the user
being able to see how it was computed.
