# Subtask 01.0/01 - Source note & legal/source-policy gate

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Security Auditor · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Document the source and close the milestone's
[legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
for `stackoverflow-tags` before any code enables network fetching.

## Baseline

`docs/source-notes/{tiobe,pypl,redmonk,stackoverflow-survey}.md` use a flat bullet format
(What it measures / Official source / … / Last verified date). No note exists for tag activity.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `docs/source-notes/stackoverflow-tags.md` | Source note + policy gate record |

## Symbols / fields

Required bullets (same keys as existing notes, plus the gate block):

| Key | Required content |
|-----|------------------|
| What it measures | Monthly count of new questions per language tag; share of a stated denominator |
| Official source | `https://api.stackexchange.com/2.3/questions`, SEDE |
| Historical availability | 2008-09 onward (fetch target: last 10 years) |
| Acquisition mechanism | `api` (default) / `sede` manual import |
| Imported metrics | `stackoverflow-tags-questions`, `stackoverflow-tags-question-share`, `stackoverflow-tags-rank` |
| Denominators | `all_questions` (api) vs `tracked_language_union` (sede) - never mixed |
| Terms/automation | API quota (300/day anon, 10k/day with key), `backoff` honoured, no scraping of stackoverflow.com HTML, data dump not used (login + non-LLM clause since 2024-07) |
| Redistribution | Aggregate counts only; no question bodies stored; CC BY-SA attribution string |
| Gate verdict | `approved-for-scheduled-fetch` / `manual-only` + reviewer + date |
| Last verified date | ISO date |

## Behaviour & validators

1. The note states the gate verdict explicitly; subtask 04 may only enable unattended fetch
   if the verdict is `approved-for-scheduled-fetch`.
2. The request-rate budget is written as a number (requests/day) that subtask 04 enforces.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | `python3 scripts/check_doc_links.py docs/source-notes/stackoverflow-tags.md` reports 0 problems |

## Success criteria

- [ ] `docs/source-notes/stackoverflow-tags.md` exists with every key above.
- [ ] Gate verdict, rate budget and redistribution stance are explicit.
- [ ] Link check clean.

## Constraints

- Do not quote or store any user-contributed content; counts only.
- Absolute-from-root links per [docs/roadmap/README.md](/docs/roadmap/README.md#linking-convention).

## Out of scope

- A structured front-matter schema for source notes - planned in the research tooling
  milestone, not here.
