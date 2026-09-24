# Task 01.0 - Source Note Schema & Candidate Registry

**Milestone:** [0007 - Source Research Tooling](/docs/roadmap/0007-source-research-tooling/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0007-source-research-tooling/plan.md#task-010---source-note-schema--candidate-registry) ·
**Category:** research-docs · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                            | Role          | Depends on | Status         |
|----|----------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [Front-matter schema, rubric & template](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/01-front-matter-schema-and-template.md) | Architect     | -          | ⬜ Not started |
| 02 | [Source-notes validator script](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/02-source-notes-validator.md)                     | Python Expert | 01         | ⬜ Not started |
| 03 | [Backfill existing & planned source notes](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/03-backfill-existing-source-notes.md)  | Docs Writer   | 01, 02     | ⬜ Not started |
| 04 | [Candidate registry generation](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/04-candidate-registry-generation.md)              | Python Expert | 02, 03     | ⬜ Not started |
| 05 | [CI & hook wiring](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/05-ci-and-hook-wiring.md)                                      | Python Expert | 04         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Give every language-ranking source a uniform, validated description: what it measures, how
to get it, under what license, since when, and how often. Score each source on one rubric so
"which source should become a provider next?" is answered from data rather than memory. The
front matter is the contract that the researcher agent (Task 02.0), the scaffold (Task 04.0)
and the watch loop (Task 05.0) all read.

## Baseline (what already exists)

- `docs/source-notes/{tiobe,pypl,redmonk,stackoverflow-survey}.md` are prose bullet lists
  with a shared set of labels ("What it measures", "Official source", "Last verified
  date", ...). There is no front matter and no machine validation.
- `docs/source-notes/.gitkeep` exists, but there is no template.
- `scripts/check_doc_links.py` is the model for a stdlib-only doc validator:
  - `argparse`;
  - `REPO_ROOT = Path(__file__).resolve().parent.parent`;
  - exit status 1 on findings;
  - `file:line` messages.
- `.claude/hooks/doc_link_check.py` is the model for a non-blocking PostToolUse hook: it
  exits 0 and surfaces problems as a reminder.
- `.github/workflows/ci.yml` runs ruff, format, mypy and pytest. It has no doc checks yet.
- The seed survey is [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md).
  It is authored separately and this task does not edit it.

## Design notes

- **Front matter over a separate YAML/JSON registry.** The note stays the single source of
  truth, and humans edit one file. The registry (`docs/research/source-candidates.md`) is
  *generated* from the notes and checked for staleness, never hand-edited.
- **Restricted YAML subset, stdlib parser.** The subset is:
  - `key: scalar`;
  - `key: [a, b]` inline lists;
  - `key: null`;
  - one level of nested map, used only for `scores:`, with two-space-indented `sub: int`
    lines;
  - `#` comments.

  Anything else is a validation error. This avoids adding PyYAML to a repo whose `scripts/`
  are dependency-free, and the error forces notes to stay simple.
- **`source_id` vs `provider_id`.** `source_id` is the note's stable slug and matches the
  filename. `provider_id` is the `ProviderRegistry` key once the source is registered, and
  `null` before that. Existing notes use the same value for both, e.g. `stackoverflow-survey`.
- **Scores are advisory.** The registry sorts by `status`, then `priority`, then total
  score. It never auto-promotes a candidate.

### Open questions

- Should `rejected`/`defunct` notes stay in `docs/source-notes/`? **Default: yes.** The
  reason for rejection is research worth keeping; the registry lists them in a separate
  section.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `python scripts/check_source_notes.py --check` exits 0 on the repo, and exits 1 on each
      seeded defect fixture.
- [ ] `docs/research/source-candidates.md` is generated, and CI fails when it is stale.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md) - seed survey
- [Milestone 0001 legal / source-policy gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
- [docs/providers.md](/docs/providers.md)
