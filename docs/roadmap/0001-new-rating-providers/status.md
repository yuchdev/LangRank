# Milestone 0001 - New Rating Providers - Status

Tracks progress against [plan.md](/docs/roadmap/0001-new-rating-providers/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                    | Status         | Tests |
|------|--------------------------------------------|----------------|-------|
| 01.0 | Stack Overflow Tags Provider                | ✅ Complete | `test_stackoverflow_tags_{metadata,fetch,normalize,validate}.py`, `test_http.py`, `test_cache.py`, `contract/test_stackoverflow_tags_provider.py` |
| 02.0 | GitHub Provider                             | ✅ Complete | `test_github_{metadata,innovation_graph,innovation_graph_normalize,octoverse,validate}.py`, `test_periods.py`, `contract/test_github_provider.py` |
| 03.0 | IEEE Spectrum Provider                      | 🔶 In progress (2/8 subtasks) | -     |
| 04.0 | JetBrains Developer Ecosystem Provider      | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet. Baseline this milestone builds
on is already merged: the `RatingProvider` protocol, `ProviderRegistry`, five
bootstrap providers (`demo`, `tiobe`, `pypl`, `redmonk`,
`stackoverflow-survey`), `Database`/migrations, and the
`FetchService`/`QueryService`/`ValidationService`/`StatusService` layer (PR #3,
`be77d0d` "feat: add first production provider implementations"). CI (ruff
check, ruff format --check, mypy, pytest) is green on that baseline.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see
  [docs/roadmap/README.md](/docs/roadmap/README.md) for the full set of
  sibling milestones it was split into). It keeps the `0001` slot because
  it's the foundation the other five build on.
- **Recommended order:** Stack Overflow tags → GitHub → IEEE Spectrum →
  JetBrains, but the four tasks are independent and may be picked up in any
  order or in parallel.
- **Legal/source-policy review is a per-task closing gate,** not a standalone
  task — it must be documented before any task enables unattended scheduled
  fetching for its source.
- **2026-09-25 - Phase R audit (implement-milestone run):** all 35 subtask specs present, no
  decomposition gaps; as-built probe found all four tasks absent (no divergence); schema stays at
  version 2, no migration required. Execution order 01.0 → 02.0 → 03.0 → 04.0 (01.0 lands the
  shared helpers the others reuse).
- **2026-09-25 - Ruling (user):** IEEE `HTML`, `Arduino`, `Verilog`, `VHDL` go into
  `IEEE_UNTRACKED_LABELS` (not added to the canonical catalog) - resolves the open choice in
  03.0/02.
- **2026-09-25 - Ruling (user):** live network calls are allowed during development to capture
  real fixtures (small, rate-limited, unauthenticated); live tests remain opt-in via the
  `integration` marker.
- **2026-09-25 - Coverage floor:** repo-root `.coveragerc` repointed from the carried-over
  `src/aegis_swr` to `src/langrank`, `fail_under` set to the measured baseline (73%) as a
  regression guard; raising it to 85% remains Milestone 0005 Task 06.0.
- **2026-09-25 - 01.0/02 deviation (verify-subtask PARTIAL):** `visual-basic` was not added to
  the canonical catalog. `_normalize_key` strips hyphens/spaces, so `visual-basic` collides with
  the pre-existing global alias `"visual basic" → vb.net` (the new collision guard raises).
  Classic VB vs VB.NET separation is open: it needs either a distinct canonical key or an
  explicit re-mapping of the bootstrap `"visual basic"` alias (a source-interpretation change for
  TIOBE). Not needed by any 0001 task.
- **2026-09-25 - 02.0/07 ruling (loop, source interpretation):** GitHub-authored, explicitly
  numbered ranking labels in an Octoverse chart's published alt text (2024: `Python (1)` …
  `Go (10)`) count as published text, not chart extraction; chart-geometry/pixel extraction stays
  forbidden. Editions without numbered text (2025 ranks 4+, 2023 and earlier) are omitted, never
  guessed. Recorded per edition in [docs/source-notes/github.md](/docs/source-notes/github.md).

## Decomposition tree (as planned)

Every task is decomposed into a task `README.md` (with a `## Subtasks` table) and one spec
file per subtask, per [docs/roadmap/README.md](/docs/roadmap/README.md)'s convention. All
subtasks are ⬜ Not started.

```
docs/roadmap/0001-new-rating-providers/
├── plan.md
├── status.md
├── 01.0-stack-overflow-tags-provider/   (8 subtasks)
│   ├── README.md
│   ├── 01-source-note-and-policy-gate.md
│   ├── 02-rating-scoped-aliases.md          ← shared: try_resolve / rating-scoped aliases
│   ├── 03-metadata-and-registry.md
│   ├── 04-fetch-api-and-offline-cache.md    ← shared: load_cached_payload, get_json
│   ├── 05-parse-and-normalize.md
│   ├── 06-validate.md
│   ├── 07-fixtures-and-contract-tests.md    ← shared: tests/contract/_golden.py
│   └── 08-docs.md
├── 02.0-github-provider/                (10 subtasks)
│   ├── README.md
│   ├── 01-source-note-and-policy-gate.md
│   ├── 02-quarterly-granularity.md          ← Granularity.QUARTER (no migration)
│   ├── 03-linguist-aliases.md
│   ├── 04-metadata-variants-and-registry.md
│   ├── 05-innovation-graph-fetch-and-parse.md
│   ├── 06-innovation-graph-normalize.md
│   ├── 07-octoverse-annual-rankings.md
│   ├── 08-validate.md
│   ├── 09-fixtures-and-contract-tests.md
│   └── 10-docs.md
├── 03.0-ieee-spectrum-provider/         (8 subtasks)
│   ├── README.md
│   ├── 01-source-note-and-policy-gate.md
│   ├── 02-ieee-aliases.md
│   ├── 03-metadata-profiles-and-registry.md
│   ├── 04-curated-dataset-and-fetch.md
│   ├── 05-parse-and-normalize.md
│   ├── 06-validate.md
│   ├── 07-fixtures-and-contract-tests.md
│   └── 08-docs.md
└── 04.0-jetbrains-provider/             (9 subtasks)
    ├── README.md
    ├── 01-source-note-and-policy-gate.md
    ├── 02-survey-question-registry.md
    ├── 03-jetbrains-aliases.md
    ├── 04-metadata-and-registry.md
    ├── 05-published-percentages.md
    ├── 06-raw-data-import.md
    ├── 07-validate.md
    ├── 08-fixtures-and-contract-tests.md
    └── 09-docs.md
```

**Cross-task subtask dependencies:** Tasks 02.0-04.0 reuse three helpers specified in Task
01.0 (subtasks 02, 04, 07). Whichever task starts first lands them per the 01.0 spec; the
tasks otherwise remain parallelizable.

## Per-task detail

### Task 01.0 - Stack Overflow Tags Provider (✅ 2026-09-25)

**Delivered**
- `stackoverflow-tags` provider (`providers/stackoverflow_tags.py`): metrics
  `stackoverflow-tags-questions` (raw), `-question-share` and `-rank` (both `is_derived`, with
  `derivation_method` naming the denominator); `api` fetch + `sede` manual import
  (`langrank import`), never mixing denominators (`all_questions` vs `tracked_language_union`).
- Shared helpers reused by 02.0-04.0: rating-scoped aliases + `LanguageNormalizer.try_resolve`
  (23 new canonical languages, collision guard); `HttpClientFactory.get_json` (host-pinned, no
  redirects, size-capped, key-scrubbed errors); `common.load_cached_payload` (contained cache
  read-back); `tests/contract/_golden.py` (`assert_matches_golden`, `LANGRANK_UPDATE_GOLDEN=1`);
  `live` pytest marker gated on `LANGRANK_LIVE_TESTS=1`.
- Source note + policy gate (`approved-for-scheduled-fetch`, 5000 req/day keyed / 300 anon),
  threat model with re-audit and task-close review
  ([docs/security/2026-09-25-stackoverflow-tags-fetch.md](/docs/security/2026-09-25-stackoverflow-tags-fetch.md)),
  provider/data-model/test-convention docs.

**Tests / gate**
- All four CI checks green; 99 tests pass (1 live test skipped by default). Coverage 73.1% → 79.6%
  (informational).
- `/verify-subtask`: PASS ×7, PARTIAL ×1 (02 - `visual-basic` deferred, see Notes & decisions).
- `/pr-review`: feature LGTM, security CLEAR; two non-blocking suggestions fixed in `c63b452`.
- API fixture captured live 2026-09-25 (unauthenticated, counts only); SEDE fixture hand-built.

**Reconciliation note**
- 03 temporarily set the fetch-all CLI test to expect failure; 06 restored it as an offline test
  (`test_cli_fetch_all_offline_all_providers_succeed`). All eight subtask specs *consumed*.

**Follow-ups (not blocking, recorded for later milestones)**
- Pre-existing: `FetchService` reports SUCCESS / exit 0 when `validate()` rejects a batch (upsert
  silently skipped) - should surface a validation-failed status.
- Derived `rank` inherits its share's `raw_record_hash`, so `updated` counts miss rank-only
  changes (values are still rewritten correctly).
- Pre-existing: `metric_id == "rank"` comparisons in `db/repository.py` / `services/query.py`
  don't match suffixed IDs such as `stackoverflow-tags-rank` (deferred to Milestone 0006 Task 01.0).
- LOW: `langrank import` reads the whole local file without a size guard.
- SEDE query template in `docs/providers.md` not yet executed against live SEDE (login-gated).

### Task 02.0 - GitHub Provider (✅ 2026-09-25)

**Delivered**
- `github` provider (`providers/github.py`) with two independently selectable variants
  (`--source innovation-graph` default, `--source octoverse`), never conflated with each other or
  with RedMonk's GitHub component.
  - **Innovation Graph** (quarterly): fetch pinned to a validated 40-hex commit SHA (1 commits-API
    call + 1 raw CSV download), `commit_sha` + `csv_sha256` sidecar re-verified on offline
    replay; normalize to derived global `pushers` (sum over ≥100-developer economy cells),
    `share` (denominator = all published Linguist names) and `rank`, each with its
    `derivation_method`; derived rank gets its own `raw_record_hash`.
  - **Octoverse** (annual, manual-curated `providers/data/github_octoverse.csv`): raw published
    ranks (`is_derived=False`) with per-edition source URL and ranking basis - 2024 top-10,
    2025 top-3; other editions omitted (see Notes & decisions, alt-text ruling).
- `Granularity.QUARTER` + `common.quarter_period` (no migration); GitHub Linguist rating-scoped
  aliases + `GITHUB_NON_LANGUAGES`.
- Shared hardening in `util/http.py`: `get_capped_bytes` (host-pinned, no redirects, capped),
  Authorization/Bearer scrubbing, transient-only retry (429/5xx/transport) on both hardened paths;
  the unhardened `get_bytes` was removed.
- Source note + policy gate (IG `approved-for-scheduled-fetch`, Octoverse `manual-only`), threat
  model with re-audit and task-close review
  ([docs/security/2026-09-25-github-fetch.md](/docs/security/2026-09-25-github-fetch.md)),
  provider/data-model docs.

**Tests / gate**
- All four CI checks green; 190 tests pass (2 live tests skipped by default). Coverage 79.6% →
  82.5% (informational).
- `/verify-subtask`: PASS ×9, PARTIAL ×1 (05 - extra keyword-only `headers=` on
  `_resolve_commit_sha`, accepted).
- `/pr-review`: feature LGTM, security CLEAR; follow-ups fixed in `b735371` (retry only transient
  failures) and `efe3325` (remove `get_bytes`, `ParseError` on unknown cached variant, Octoverse
  discoverability).
- Innovation Graph fixture captured live 2026-09-25 at commit `054c7dbc…` (trimmed, no edits).

**Reconciliation note**
- 04 temporarily set the fetch-all CLI test to expect `github` FAILED; 08 restored
  `test_cli_fetch_all_offline_all_providers_succeed` (all providers SUCCESS, offline). The fixture
  provenance file is `tests/fixtures/github/SOURCE.md` per spec 09. All ten subtask specs
  *consumed*.

**Follow-ups (not blocking)**
- Pre-existing `metric_id == "rank"` literals in `services/query.py` / `plotting/service.py` make
  `--top`, `--top-current`, `--invert-rank` no-ops for suffixed rank metrics (Milestone 0006
  Task 01.0).
- Octoverse partial editions (2025 top-3 vs 2024 top-10) are not flagged by any validator; a
  year-over-year edition-size note could help curators.
- 429 retries use fixed exponential backoff, not the server's `Retry-After` value.

