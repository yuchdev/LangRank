# Subtask 01.0/05 - Record verified breaks for bootstrap providers

**Task:** [01.0 - Methodology Break Tracking](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Replace the placeholder "import" notes of the bootstrap providers with researched, cited
methodology segments, so at least one rating carries a real break (milestone exit criterion).

## Baseline

- `tiobe`, `pypl`, `redmonk`, `stackoverflow-survey` each declare one note (e.g.
  `2026-v1`) that describes the import process, not the upstream methodology.
- Source notes live in `docs/source-notes/{tiobe,pypl,redmonk,stackoverflow-survey}.md`.

## Files

| Action | Path                                              | Purpose |
|--------|---------------------------------------------------|---------|
| Modify | `src/langrank/providers/tiobe.py`                 | `methodology_notes` list |
| Modify | `src/langrank/providers/pypl.py`                  | `methodology_notes` list |
| Modify | `src/langrank/providers/redmonk.py`               | `methodology_notes` list |
| Modify | `src/langrank/providers/stackoverflow_survey.py`  | `methodology_notes` list (wording changes, `affects_metrics`) |
| Modify | `src/langrank/providers/demo.py`                  | One synthetic `method_change` break for tests (clearly labeled synthetic) |
| Modify | `docs/source-notes/*.md`                          | New `## Methodology history` section per source, with citation per break |
| Modify | `tests/contract/test_production_providers.py`     | Contract tests |

## Symbols / fields

| Symbol                                         | Kind  | Type / signature        | Default | Notes |
|------------------------------------------------|-------|-------------------------|---------|-------|
| `<Provider>.metadata().methodology_notes`      | field | `list[MethodologyNote]` | -       | segments ordered by `valid_from`, non-overlapping per metric |

## Behaviour & validators

1. Every non-`initial` note has a non-empty `source_url` and a matching bullet in the
   source note (`version`, `valid_from`, what changed, citation URL, date verified).
2. Candidate breaks to **verify before recording** (do not record if unverifiable):
   TIOBE search-engine/qualification changes; Stack Overflow Survey question wording and
   respondent-population changes between years; RedMonk data-source changes (e.g. GitHub
   metric definition). If research finds none for a source, keep one `initial` segment and
   document "no known break as of <date>". Leads already found by the source survey
   ([docs/research/language-ranking-sources.md](/docs/research/language-ranking-sources.md)):
   RedMonk's H2-2025 GitHub pull-request component (RedMonk calls it "anomalously low"; likely
   cause is GitHub's 2025-10-07 Events API change dropping repo language from GH Archive
   `PullRequestEvent` payloads) and RedMonk's move to effectively annual editions (no June 2023
   or June 2025 edition).
3. The demo break is described as synthetic in both `description` and the demo docstring.
4. Segments of one provider satisfy the non-overlap rule of subtask 04.

## Tests

| Test function                                           | File                                           | Type     | Asserts |
|---------------------------------------------------------|------------------------------------------------|----------|---------|
| `test_provider_methodology_notes_non_overlapping`       | `tests/contract/test_production_providers.py`  | Unit     | parametrized over all providers |
| `test_non_initial_breaks_have_source_url`               | `tests/contract/test_production_providers.py`  | Unit     | parametrized over all providers |
| `test_demo_declares_synthetic_break`                    | `tests/contract/test_demo_provider.py`         | Unit     | one `method_change` note |

## Success criteria

- [ ] At least one production rating declares a cited non-`initial` break.
- [ ] Each touched source note has a `## Methodology history` section.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No fabricated facts: a break without a citation is not added. This mirrors the "never
  fabricate" rule in [CLAUDE.md](/CLAUDE.md).
- `parser_version` does not change (metadata-only change).

## Out of scope

- Breaks for providers added by [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) — each provider task records its own.
