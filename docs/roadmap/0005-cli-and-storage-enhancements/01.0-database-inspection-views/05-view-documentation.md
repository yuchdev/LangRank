# Subtask 01.0/05 - Document the views in `docs/data-model.md`

**Task:** [01.0 - Database Inspection Views](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md) ·
**Role:** Docs Writer · **Depends on:** 01, 02, 03 · **Status:** ⬜ Not started

## Goal

Give users a copy-pasteable reference for inspecting the DB with plain `sqlite3`: what each view
means, its columns, and example queries.

## Baseline

- [docs/data-model.md](/docs/data-model.md) documents tables; views are not described.

## Files

| Action | Path                   | Purpose |
|--------|------------------------|---------|
| Modify | `docs/data-model.md`   | New `## Inspection views` section |
| Modify | `README.md`            | One-line pointer under the query/inspection usage section |

## Symbols / fields

| Symbol                         | Kind    | Notes |
|--------------------------------|---------|-------|
| `## Inspection views`          | heading | One `###` per view: purpose, "latest" semantics, column table, example query |

## Behaviour & validators

1. Each of the five views has: a one-sentence purpose, its column list (matching `PRAGMA table_info`),
   and one example `sqlite3 "$LANGRANK_DB" "..."` command.
2. The docs state explicitly that `latest_observations` is latest-per-language while
   `latest_language_ranks` is latest-period-per-metric, and that rank metrics are identified by
   `unit = 'rank'`.
3. The docs warn that ranks from different ratings are not comparable (link README's methodology
   warning).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (link check)  | `scripts/check_doc_links.py docs/` | - | No new dangling links |

## Success criteria

- [ ] Section exists with all five views; column lists match the migrations.
- [ ] `python3 scripts/check_doc_links.py docs/` reports no new problems.

## Constraints

- Absolute-from-repo-root links (`/docs/...`) per [docs/roadmap/README.md](/docs/roadmap/README.md).

## Out of scope

- API reference for `Database` methods.
