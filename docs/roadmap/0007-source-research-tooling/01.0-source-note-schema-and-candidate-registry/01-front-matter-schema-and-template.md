# Subtask 01.0/01 - Front-matter Schema, Rubric & Template

**Task:** [01.0 - Source Note Schema & Candidate Registry](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/README.md) ·
**Role:** Architect · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Define the source-note front-matter schema and the scoring rubric, and publish them as
`docs/source-notes/README.md` (the reference) plus `docs/source-notes/TEMPLATE.md` (the
copy-me file).

## Baseline

- The existing notes are prose-only, and there is no `docs/source-notes/README.md`.
- The fields the schema must cover come from the existing note labels and from the
  [Milestone 0001 source-policy gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).
  That gate asks for:
  - official API/download availability;
  - robots policy;
  - terms of use;
  - request rate;
  - whether redistribution is allowed.

## Files

| Action | Path                              | Purpose                                                        |
|--------|-----------------------------------|----------------------------------------------------------------|
| Create | `docs/source-notes/README.md`     | Schema reference: every field, type, allowed values, rubric    |
| Create | `docs/source-notes/TEMPLATE.md`   | Copyable note with every field and the required body sections  |
| Delete | `docs/source-notes/.gitkeep`      | Directory is no longer empty                                   |

## Symbols / fields

Front-matter fields (all required unless noted):

| Field                       | Type                    | Allowed values / format                                                                                          | Notes |
|-----------------------------|-------------------------|------------------------------------------------------------------------------------------------------------------|-------|
| `source_id`                 | str                     | kebab-case, equals filename stem                                                                                 | Stable forever |
| `provider_id`               | str \| null             | `ProviderRegistry` key                                                                                           | `null` until registered |
| `display_name`              | str                     | free text                                                                                                        | |
| `status`                    | enum                    | `existing`, `planned`, `candidate`, `rejected`, `defunct`                                                        | `existing` requires non-null `provider_id` |
| `measures`                  | enum                    | `search-visibility`, `tutorial-search`, `qa-activity`, `code-hosting-activity`, `package-ecosystem`, `self-reported-usage`, `job-demand`, `composite`, `other` | |
| `access`                    | list[enum]              | subset of `api`, `bulk-download`, `html`, `pdf`, `chart-only`, `manual`                                          | Non-empty |
| `license`                   | str                     | SPDX id, `proprietary`, or `unknown`                                                                             | |
| `redistribution`            | enum                    | `allowed`, `derived-only`, `forbidden`, `unknown`                                                                | Feeds release bundling (Milestone 0004) |
| `terms_url`                 | str \| null             | `https://` URL                                                                                                   | Required when `status` ∈ {`existing`, `planned`} |
| `automation`                | enum                    | `allowed`, `rate-limited`, `discouraged`, `forbidden`, `unknown`                                                 | Required when `status` ∈ {`existing`, `planned`} |
| `history_start`             | str \| null             | `YYYY` or `YYYY-MM`                                                                                              | |
| `granularity`               | enum                    | `month`, `quarter`, `half-year`, `year`, `snapshot`                                                              | |
| `cadence`                   | enum                    | `monthly`, `quarterly`, `semiannual`, `annual`, `irregular`, `none`                                              | `none` for defunct sources |
| `typical_publication_month` | list[int] \| null       | 1-12 each                                                                                                        | Read by Task 05.0; `null` when `cadence` is `monthly` or `irregular` |
| `homepage`                  | str                     | `https://` URL                                                                                                   | |
| `last_verified`             | str                     | ISO date `YYYY-MM-DD`, not in the future                                                                         | |
| `priority`                  | enum                    | `p0`, `p1`, `p2`, `p3`, `none`                                                                                   | `none` for `rejected`/`defunct` |
| `roadmap`                   | str \| null             | repo-root path to a plan.md or task README                                                                       | Must exist when set |
| `scores`                    | map[str, int]           | keys = rubric dimensions below, values 1-5                                                                       | All six keys required |

Rubric dimensions (`scores.*`). Each gets 1-5 anchors described in the README:

| Key                   | 1 means                                   | 5 means                                              |
|-----------------------|-------------------------------------------|------------------------------------------------------|
| `distinctness`        | duplicates a signal we already store      | measures something no stored rating covers           |
| `history_depth`       | < 2 years                                 | ≥ 10 years of consistent history                     |
| `machine_readability` | chart images only                         | documented API / bulk CSV                            |
| `license_clarity`     | no terms found                            | explicit open license (e.g. CC-BY, CC0)              |
| `methodology`         | undocumented                              | published, versioned methodology                     |
| `continuity`          | defunct or ad-hoc                         | multi-year stable publisher and schedule             |

Required body sections, in order:

- `## What it measures`
- `## Access & acquisition`
- `## Terms, robots & redistribution`
- `## History & methodology changes`
- `## Language naming quirks`
- `## Known limitations`
- `## Sources` (a list of cited URLs, each with an access date)

## Behaviour & validators

1. The README documents each cross-field rule from the table above. These rules are
   enforced in [subtask 02](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/02-source-notes-validator.md).
2. The README states the restricted YAML subset explicitly, and says that nothing else is
   parsed. See the task README's design notes.
3. The README restates the "cite or mark `(unverified)`" rule and the measurement-type
   honesty rule from
   [plan.md § Shared conventions](/docs/roadmap/0007-source-research-tooling/plan.md#shared-conventions).
4. `TEMPLATE.md` has `source_id: TEMPLATE`. The validator skips it by name. The template
   still uses placeholder values that would be valid if filled in.

## Tests

None in this subtask (docs only). The template becomes a validator fixture in subtask 02.

## Success criteria

- [ ] `docs/source-notes/README.md` lists all 19 fields, all 6 rubric keys with 1/3/5
      anchors, and all 7 body sections.
- [ ] `docs/source-notes/TEMPLATE.md` contains every field and every section heading.
- [ ] `python3 scripts/check_doc_links.py docs/source-notes` exits 0.

## Constraints

- Schema field names are snake_case and stable. Renaming one later requires updating Tasks
  02.0, 04.0 and 05.0.
- [CLAUDE.md](/CLAUDE.md) measurement-type rule: `measures` is single-valued. A source with
  several families (e.g. JetBrains usage vs. primary language) still has one `measures`
  value, and its body section explains the families.

## Out of scope

- Converting the existing notes: [subtask 03](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/03-backfill-existing-source-notes.md).
