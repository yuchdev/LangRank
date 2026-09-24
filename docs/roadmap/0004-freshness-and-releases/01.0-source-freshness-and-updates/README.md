# Task 01.0 - Source Freshness Monitoring & Scheduled Updates

**Milestone:** [0004 - Freshness & Releases](/docs/roadmap/0004-freshness-and-releases/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates) ·
**Category:** ops · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                               | Role          | Depends on | Status         |
|----|---------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [Freshness result model & probe protocol](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/01-freshness-model.md) | Python Expert | -          | ⬜ Not started |
| 02 | [Conditional HTTP probe & artifact validators](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/02-conditional-http-probe.md) | Python Expert | 01         | ⬜ Not started |
| 03 | [Per-provider freshness probes](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/03-provider-freshness-probes.md) | Python Expert | 01, 02     | ⬜ Not started |
| 04 | [StatusService freshness & `status --json`](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/04-status-json.md) | Python Expert | 03         | ⬜ Not started |
| 05 | [Scheduled-fetch source policy](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/05-scheduled-fetch-policy.md) | Security Auditor | 01      | ⬜ Not started |
| 06 | [UpdateService pipeline](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/06-update-service.md) | Python Expert | 04, 05     | ⬜ Not started |
| 07 | [`langrank update` command](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/07-update-cli.md) | Python Expert | 06         | ⬜ Not started |
| 08 | [Scheduled-update docs & example workflow](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/08-scheduled-update-docs.md) | Docs Writer   | 07         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Answer "does this source have data we don't have yet?" per provider without a full
re-download, expose that answer through `langrank status` (table and `--json`), and add a
`langrank update` command that fetches **only** stale providers, validates, reports
methodology changes, and emits a summary - safe to run from cron/CI, and never scheduling
fetches against sources whose terms discourage automation.

## Baseline (what already exists)

- `src/langrank/services/status.py:StatusService.statuses()` computes `provider_state`
  (`current`/`stale`/`ready`/`unknown`) by string-prefix comparison against
  `provider.upstream_latest_period()`, discovered via `hasattr(...)` special-casing.
- Every provider hardcodes `upstream_latest_period()` (`tiobe`/`pypl` → `"2025-12"`,
  `redmonk` → `"2025-06"`, `stackoverflow-survey` → `"2025"`, `demo` → `"2026"`). These are
  not freshness signals - they are constants that silently go stale.
- Production providers read bundled CSV snapshots from `src/langrank/providers/data/`
  (`fetch()` never touches the network). `util/http.py:HttpClientFactory` exists but no
  code calls it.
- `models.RawArtifact` has `http_etag`/`http_last_modified`, the `raw_artifacts` table has
  matching columns, and `Database.record_raw_artifact` writes them - but
  `providers/common.py:payload_from_content` never sets them, so they are always `NULL`.
- `langrank status` (`cli.py:status`) renders a Rich table only; no `--json`.
- `FetchService.fetch` already records `fetch_runs` and upserts metadata incl.
  `methodology_notes` (via `Database.upsert_provider_metadata`).

## Design notes

- **Freshness is compute-on-read.** No new table: a `FreshnessCheck` is produced per
  invocation and rendered/serialized. Persisting history of checks is out of scope.
- **Interim capability detection.** Milestone 0006
  [Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata)
  will add a structured `capabilities()` with `supports_status_check`. Until it lands, a
  `@runtime_checkable` `FreshnessProbe` Protocol in `providers/base.py` plus the helper
  `providers/common.py:freshness_probe_for(provider)` (an `isinstance` check) is the single
  place that decides whether a provider can be probed. When 0006/01.0 lands, only that
  helper changes to read `capabilities().supports_status_check`. No other code may use
  `hasattr` on providers.
- **Two mechanisms, offline first.** `bundled_snapshot` (offline; upstream-latest is the
  max period in the bundled CSV - replaces the hardcoded constants) and `http_conditional`
  (opt-in `--online`; HEAD with `If-None-Match`/`If-Modified-Since`, never a body
  download). Additional mechanisms named by the plan (archive-index, survey-year page,
  release feed) are added per provider when that provider gains a live `fetch()` -
  milestone 0001 territory - and must reuse the same `FreshnessCheck` shape.
- **Policy gate.** `langrank update --scheduled` only fetches providers whose
  `SourcePolicy.allow_scheduled_fetch` is `True`; the default is `False` for every
  provider until its [legal / source-policy review](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
  says otherwise. Interactive `langrank update` (no `--scheduled`) is a manual action.
- **Idempotency** comes from freshness: a second run after a successful update sees every
  provider `fresh` and performs zero fetches.

### Open questions

- Should `unknown` freshness count as stale in `update`? **Default: no** - skip and report;
  `--include-unknown` opts in.
- Should `update` also run archival pruning (Task 03.0)? **Default: no** in this task; Task
  03.0/05 wires retention into the fetch path, which `update` inherits.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `langrank status --json` exposes a per-provider freshness signal; the default
      (offline) path makes zero network calls and `--online` makes only conditional HEAD/GET
      requests with no full-body read (asserted with `httpx.MockTransport`).
- [ ] `langrank update` is idempotent and skips providers already fresh.
- [ ] No `hasattr(provider, ...)` remains in `services/`; no hardcoded
      `upstream_latest_period` constants remain in `providers/`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- RFC 9110 §13 (conditional requests: `If-None-Match`, `If-Modified-Since`, `304`).
- httpx `MockTransport` for request-level test doubles.
- [docs/source-notes/](/docs/source-notes/tiobe.md) - per-source terms notes feeding `SourcePolicy`.
