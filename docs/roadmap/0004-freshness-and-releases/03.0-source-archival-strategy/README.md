# Task 03.0 - Source Archival Strategy

**Milestone:** [0004 - Freshness & Releases](/docs/roadmap/0004-freshness-and-releases/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-030---source-archival-strategy) ·
**Category:** governance · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                         | Role          | Depends on | Status         |
|----|---------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [Retention policy config](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/01-retention-policy-config.md) | Python Expert | -          | ⬜ Not started |
| 02 | [Raw-artifact retention migration & queries](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/02-raw-artifact-retention-schema.md) | Python Expert | -          | ⬜ Not started |
| 03 | [Pure retention planner](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/03-retention-planner.md) | Python Expert | 01, 02     | ⬜ Not started |
| 04 | [ArchivalService pruning](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/04-archival-service.md) | Python Expert | 03         | ⬜ Not started |
| 05 | [`cache` commands & post-fetch retention](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/05-cache-cli-and-fetch-hook.md) | Python Expert | 04         | ⬜ Not started |
| 06 | [Retention docs & repo size guard](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/06-retention-docs-and-repo-guard.md) | Docs Writer   | 05         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

A configurable raw-artifact retention policy - `all`, `latest`, `yearly`, `none` - set
globally with per-provider overrides, applied by a service after fetches and on demand,
that frees disk while keeping the provenance trail (`sha256`, `url`, `retrieved_at`) of
every pruned artifact in SQLite.

## Baseline (what already exists)

- `providers/common.py:payload_from_content` writes `cache_dir/<provider>-<sha12>.<ext>`
  and a `RawArtifact` with a fresh `uuid4` id on every fetch - so repeated fetches of
  identical content create **several `raw_artifacts` rows pointing at one file**. Pruning
  must never delete a file still referenced by a retained row.
- `raw_artifacts` has no retention columns; `observations` has no FK to `raw_artifacts`
  (links are by `rating_id` + time only).
- `FetchRequest.no_cache` already skips writing artifacts altogether.
- `config.py:resolve_config` precedence: CLI flag > env var > TOML `[langrank]` > XDG default.

## Design notes

- **Rows are kept, bytes are pruned.** A pruned artifact row gets
  `retention_state='pruned'` and `pruned_at`; its `sha256` remains, so provenance survives
  and a later re-download can be verified against it.
- **Default policy: `latest`** (disk-safe out of the box, still reproduces the current
  DB). `yearly` is the recommended override for large survey archives (e.g.
  `stackoverflow-survey`), declared as the provider's `default_retention` so users get it
  without configuring anything.
- **Precedence per provider:** CLI `--retention` > env `LANGRANK_RETENTION` > TOML
  `[langrank.retention] <provider_id>` > TOML `[langrank] retention` > provider
  `default_retention` > `latest`.
- **Pruning lives in a service**, never in providers (providers never touch the DB or
  the cache beyond writing a payload - [CLAUDE.md](/CLAUDE.md)).
- **Path safety:** only files that resolve inside `AppConfig.cache_path` are deleted.
- Migration uses the next free integer in `db/migrations.py` at implementation time
  (currently `3`; milestones 0003/0005 also add migrations - take whatever is next).

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Retention configurable globally and per provider; default is disk-safe.
- [ ] Tests cover each policy value (`all`, `latest`, `yearly`, `none`).
- [ ] No large copyrighted/raw dataset can be committed unnoticed (size guard test).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [Milestone 0001 legal / source-policy gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).
