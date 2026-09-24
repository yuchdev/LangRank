# Subtask 02.0/06 - Release Format Docs

**Task:** [02.0 - Dataset Release Workflow](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
**Role:** Docs Writer · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Document the bundle layout, every `metadata.json` field, how to verify a bundle, the
reproducibility guarantee and its SQLite caveat, and the redistribution rules.

## Baseline

- `docs/data-model.md` documents observation columns; no release docs.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `docs/releases.md` | Bundle reference |
| Modify | `docs/data-model.md` | Link to release column set |
| Modify | `README.md` | "Dataset releases" section |
| Modify | `docs/README.md` | Register `docs/releases.md` |
| Create | `tests/unit/test_release_docs.py` | Doc/schema drift guard |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `docs/releases.md` § "metadata.json fields" | doc table | one row per `ReleaseManifest` field | - | |

## Behaviour & validators

1. Verification recipe: `cd dist && sha256sum -c checksums.txt` (and `shasum -a 256 -c` on macOS).
2. States that only normalized observations ship; raw artifacts never do; forbidden-
   redistribution ratings are excluded and listed.
3. Reproducibility: identical DB + `--generated-at` (or `SOURCE_DATE_EPOCH`) → identical
   CSV/JSON/metadata bytes; SQLite is content-equivalent only.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_release_docs_list_every_manifest_field` | `tests/unit/test_release_docs.py` | Unit | every `dataclasses.fields(ReleaseManifest)` name appears in `docs/releases.md` |

## Success criteria

- [ ] `python3 scripts/check_doc_links.py docs/` reports no new problems.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Absolute-from-root links per [docs/roadmap/README.md](/docs/roadmap/README.md).

## Out of scope

- Hosting/publishing releases.
