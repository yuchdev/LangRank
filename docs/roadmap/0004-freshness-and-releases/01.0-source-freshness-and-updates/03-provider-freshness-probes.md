# Subtask 01.0/03 - Per-Provider Freshness Probes

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 02 · **Status:** ⬜ Not started

## Goal

Implement `check_freshness` on all five registered providers, deriving the upstream latest
period from real data instead of hardcoded constants, and remove every
`upstream_latest_period()` method.

## Baseline

- `tiobe.py`, `pypl.py`, `redmonk.py`, `stackoverflow_survey.py`, `demo.py` each define
  `upstream_latest_period()` returning a string literal.
- The four production providers load `providers/data/<id>.csv`; `demo` generates
  synthetic data in-process.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/providers/common.py` | `bundled_latest_period(path, column) -> str \| None`, `bundled_snapshot_check(...)`, `http_conditional_check(...)` |
| Modify | `src/langrank/providers/tiobe.py` | `check_freshness`; drop `upstream_latest_period` |
| Modify | `src/langrank/providers/pypl.py` | same |
| Modify | `src/langrank/providers/redmonk.py` | same |
| Modify | `src/langrank/providers/stackoverflow_survey.py` | same |
| Modify | `src/langrank/providers/demo.py` | `check_freshness` with `STATIC` mechanism |
| Modify | `src/langrank/models.py` | `ProviderMetadata.freshness_url: str \| None = None` |
| Create | `tests/contract/test_provider_freshness.py` | Contract tests over all providers |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `ProviderMetadata.freshness_url` | field | `str \| None` | `None` | URL probed by `http_conditional`; defaults to `homepage` when `None` |
| `bundled_latest_period` | function | `(path: Path, column: str) -> str \| None` | - | Max value of `column` in the CSV; memoised per path |
| `bundled_snapshot_check` | function | `(*, provider_id: str, bundled_period: str \| None, context: FreshnessContext) -> FreshnessCheck` | - | Mechanism `BUNDLED_SNAPSHOT`; uses `compare_periods` |
| `http_conditional_check` | function | `(*, provider_id: str, url: str, context: FreshnessContext, http: HttpClientFactory) -> FreshnessCheck` | - | Mechanism `HTTP_CONDITIONAL` |
| `<Provider>.check_freshness` | method | `(context: FreshnessContext) -> FreshnessCheck` | - | On all 5 providers |

## Behaviour & validators

1. **Offline (`context.online is False`)** - production providers return
   `bundled_snapshot_check` using their CSV's max period (`period` column for monthly
   sources, `year` for annual - whichever column the provider's `parse()` already reads).
   Result: `STALE` if the local DB lags the bundled snapshot (a `fetch` would add data),
   else `FRESH`.
2. **Online (`context.online is True`)** - production providers additionally call
   `http_conditional_check` on `freshness_url or homepage`:
   `not_modified` → keep the bundled verdict; `2xx` with a changed validator → `STALE`
   with `detail="upstream page changed since last artifact"` and
   `upstream_latest_period=None` (we know it changed, not to which period - never guess).
   `FetchError` → `ERROR` with `detail=str(exc)`; never raised to the caller.
3. **No prior validators** (first online run): a `2xx` yields `UNKNOWN` with
   `detail="no stored validator to compare"` - not `STALE`.
4. `demo` returns `FRESH` with mechanism `STATIC` when local data exists, `STALE` when none.
5. After this subtask, `grep -rn "upstream_latest_period()" src/` finds nothing, and
   `services/status.py` is updated minimally to call `freshness_probe_for` (full rewrite in 04).
6. Probes never write to SQLite and never read the DB - they only see `FreshnessContext`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_every_registered_provider_is_a_freshness_probe` | `tests/contract/test_provider_freshness.py` | Unit | `freshness_probe_for(p)` not `None` for all `ProviderRegistry.all()` |
| `test_offline_probe_makes_no_network_calls` | same | Mock | MockTransport handler that raises is never invoked with `online=False` |
| `test_bundled_snapshot_stale_when_db_empty` | same | Unit | `local_latest_period=None` → `STALE` with bundled period set |
| `test_bundled_snapshot_fresh_after_fetch` | same | Integration | fetch into temp DB, then probe → `FRESH` |
| `test_online_probe_not_modified_keeps_bundled_verdict` | same | Mock | 304 path |
| `test_online_probe_changed_validator_is_stale_without_period` | same | Mock | `upstream_latest_period is None` |
| `test_online_probe_first_run_is_unknown` | same | Mock | rule 3 |
| `test_online_probe_error_is_reported_not_raised` | same | Mock | `state == ERROR` |

## Success criteria

- [ ] All five providers implement `check_freshness`; no `upstream_latest_period` remains.
- [ ] Offline default is network-free (test-enforced).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Providers stay DB-free; network only inside `fetch()`/`check_freshness()` and only when
  `context.online` ([CLAUDE.md](/CLAUDE.md)).
- A probe never fabricates an `upstream_latest_period`.

## Out of scope

- Archive-index / survey-year-page / release-feed mechanisms - added alongside live
  `fetch()` implementations in [milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md).
