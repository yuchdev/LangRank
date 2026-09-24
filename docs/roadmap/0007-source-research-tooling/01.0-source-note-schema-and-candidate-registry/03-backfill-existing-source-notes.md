# Subtask 01.0/03 - Backfill Existing & Planned Source Notes

**Task:** [01.0 - Source Note Schema & Candidate Registry](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/README.md) ·
**Role:** Docs Writer · **Depends on:** 01, 02 · **Status:** ⬜ Not started

## Goal

Convert the four existing notes to the new schema without losing any existing statement.
Add schema-valid `planned` notes for the four
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) sources.

## Baseline

- The existing notes are `docs/source-notes/tiobe.md`, `pypl.md`, `redmonk.md` and
  `stackoverflow-survey.md`. All are prose, and all were last verified 2026-09-06.
- Metric IDs and parser versions already recorded in these notes (e.g. `tiobe-v1`,
  `pypl-share`) must be preserved in the body.
- Seed facts for the new notes come from
  [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md).

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Modify | `docs/source-notes/tiobe.md`                 | Add front matter; restructure body into the required sections |
| Modify | `docs/source-notes/pypl.md`                  | same |
| Modify | `docs/source-notes/redmonk.md`               | same |
| Modify | `docs/source-notes/stackoverflow-survey.md`  | same |
| Create | `docs/source-notes/stackoverflow-tags.md`    | `status: planned`, `roadmap:` → Milestone 0001 plan |
| Create | `docs/source-notes/github.md`                | `status: planned` (Octoverse + Innovation Graph variants in body) |
| Create | `docs/source-notes/ieee-spectrum.md`         | `status: planned` |
| Create | `docs/source-notes/jetbrains.md`             | `status: planned` |

## Symbols / fields

For the existing notes, set `status: existing` and set `provider_id` to the registry key
(`tiobe`, `pypl`, `redmonk`, `stackoverflow-survey`). `measures` values:

| Note                  | `measures`              | `granularity` | `cadence`    |
|-----------------------|-------------------------|---------------|--------------|
| `tiobe`               | `search-visibility`     | `month`       | `monthly`    |
| `pypl`                | `tutorial-search`       | `month`       | `monthly`    |
| `redmonk`             | `composite`             | `snapshot`    | `semiannual` |
| `stackoverflow-survey`| `self-reported-usage`   | `year`        | `annual`     |
| `stackoverflow-tags`  | `qa-activity`           | `month`       | `monthly`    |
| `github`              | `code-hosting-activity` | `year`        | `annual`     |
| `ieee-spectrum`       | `composite`             | `year`        | `annual`     |
| `jetbrains`           | `self-reported-usage`   | `year`        | `annual`     |

## Behaviour & validators

1. Every bullet in the old prose notes survives in a body section, reworded where needed.
   None is dropped.
2. Facts that cannot be verified from a cited URL during the backfill are kept and suffixed
   `(unverified)`. `last_verified` changes only for notes whose URLs were actually rechecked.
3. `scores` values are an initial estimate. The body's `## Sources` section justifies each
   `license_clarity` and `machine_readability` score.

## Tests

| Test function                         | File                                       | Type | Asserts |
|---------------------------------------|--------------------------------------------|------|---------|
| `test_repo_source_notes_are_valid`    | `tests/scripts/test_check_source_notes.py` | Unit | `load_notes()` on the real `docs/source-notes` returns 8 notes and 0 problems |
| `test_existing_notes_match_registry`  | same                                       | Unit | The `provider_id`s of `status: existing` notes equal the non-demo keys of `ProviderRegistry(tmp_path)._providers` |

## Success criteria

- [ ] `python scripts/check_source_notes.py --check` exits 0.
- [ ] 8 notes exist, with 4 `existing` and 4 `planned`.
- [ ] The old "Parser/version notes" and "Imported metrics" lines are still present
      (verify with `grep -l "tiobe-v1" docs/source-notes/tiobe.md`).

## Constraints

- Do not invent license or terms facts. Use `unknown` plus `(unverified)` instead.
- `demo` gets no source note. It is synthetic and has no upstream source.

## Out of scope

- Candidate (non-planned) sources. Those are added through `/source-research` in Task 02.0.
