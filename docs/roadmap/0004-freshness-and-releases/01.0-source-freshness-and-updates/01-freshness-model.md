# Subtask 01.0/01 - Freshness Result Model & Probe Protocol

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Introduce the domain types every later subtask shares: a `FreshnessState` enum, an
immutable `FreshnessCheck` result, the `FreshnessContext` input, and an optional,
runtime-checkable `FreshnessProbe` provider protocol with a single detection helper that
replaces `hasattr` special-casing.

## Baseline

- `models.py` holds all frozen dataclasses/`StrEnum`s (`Granularity`, `FetchRunStatus`, ...).
- `providers/base.py:RatingProvider` is a plain `Protocol` (not runtime-checkable).
- `services/status.py` uses `hasattr(provider, "upstream_latest_period")`.

## Files

| Action | Path                                    | Purpose                                              |
|--------|-----------------------------------------|------------------------------------------------------|
| Modify | `src/langrank/models.py`                | Add `FreshnessState`, `FreshnessMechanism`, `FreshnessContext`, `FreshnessCheck` |
| Modify | `src/langrank/providers/base.py`        | Add `@runtime_checkable class FreshnessProbe(Protocol)` |
| Modify | `src/langrank/providers/common.py`      | Add `freshness_probe_for()` and `compare_periods()`  |
| Create | `tests/unit/test_freshness_model.py`    | Unit tests for the model and helpers                 |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `FreshnessState` | StrEnum | `FRESH="fresh"`, `STALE="stale"`, `UNKNOWN="unknown"`, `UNSUPPORTED="unsupported"`, `ERROR="error"` | - | `UNSUPPORTED` = provider has no probe |
| `FreshnessMechanism` | StrEnum | `BUNDLED_SNAPSHOT="bundled_snapshot"`, `HTTP_CONDITIONAL="http_conditional"`, `STATIC="static"`, `NONE="none"` | - | Extensible: archive-index / release-feed added later |
| `FreshnessContext` | frozen dataclass | fields below | - | Input passed to a probe; built by `StatusService` from the DB |
| `FreshnessContext.local_latest_period` | field | `str \| None` | `None` | ISO `period_start` of newest local observation |
| `FreshnessContext.last_etag` | field | `str \| None` | `None` | From newest `raw_artifacts` row |
| `FreshnessContext.last_modified` | field | `str \| None` | `None` | From newest `raw_artifacts` row |
| `FreshnessContext.online` | field | `bool` | `False` | Probes must not touch the network when `False` |
| `FreshnessCheck` | frozen dataclass | fields below | - | Result |
| `FreshnessCheck.provider_id` | field | `str` | - | |
| `FreshnessCheck.state` | field | `FreshnessState` | - | |
| `FreshnessCheck.mechanism` | field | `FreshnessMechanism` | - | |
| `FreshnessCheck.checked_at` | field | `datetime` (UTC) | - | |
| `FreshnessCheck.local_latest_period` | field | `str \| None` | `None` | |
| `FreshnessCheck.upstream_latest_period` | field | `str \| None` | `None` | `None` when mechanism can't know it (e.g. HTTP 200 w/o period) |
| `FreshnessCheck.http_etag` / `http_last_modified` | fields | `str \| None` | `None` | Echo of upstream validators |
| `FreshnessCheck.detail` | field | `str \| None` | `None` | Human-readable reason / error message |
| `FreshnessCheck.to_dict()` | method | `() -> dict[str, Any]` | - | JSON-safe; datetimes ISO, enums `.value` |
| `FreshnessProbe` | runtime-checkable Protocol | `def check_freshness(self, context: FreshnessContext) -> FreshnessCheck: ...` | - | Optional provider extension |
| `freshness_probe_for` | function | `(provider: RatingProvider) -> FreshnessProbe \| None` | - | The **only** capability-detection point |
| `compare_periods` | function | `(local: str \| None, upstream: str \| None) -> FreshnessState` | - | Period-granularity-aware comparison |

## Behaviour & validators

1. `compare_periods(None, x)` → `STALE` when `x` is not `None` (nothing local yet);
   `compare_periods(x, None)` → `UNKNOWN`; both `None` → `UNKNOWN`.
2. `compare_periods` compares on the **shorter** of the two period strings' precision
   (`"2025"` vs `"2025-12-01"` compares years; `"2025-06"` vs `"2025-06-01"` compares
   months) - replacing the current `str.startswith` logic, which misreports
   `local="2025-12-01"` vs `upstream="2025-1"`-style prefixes. Local ≥ upstream → `FRESH`,
   else `STALE`.
3. `freshness_probe_for` returns `provider` if `isinstance(provider, FreshnessProbe)`, else
   `None`. A docstring states it is the interim stand-in for
   `capabilities().supports_status_check` (milestone 0006 Task 01.0).
4. `FreshnessCheck` never carries fabricated periods: when a mechanism cannot determine the
   upstream period it sets `upstream_latest_period=None`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_compare_periods_fresh_when_local_equals_upstream_month` | `tests/unit/test_freshness_model.py` | Unit | `"2025-12-01"` vs `"2025-12"` → `FRESH` |
| `test_compare_periods_stale_when_local_older` | same | Unit | `"2025-06-01"` vs `"2025-12"` → `STALE` |
| `test_compare_periods_year_precision` | same | Unit | `"2025-01-01"` vs `"2025"` → `FRESH` |
| `test_compare_periods_missing_values` | same | Unit | rule 1 matrix |
| `test_freshness_probe_for_detects_protocol` | same | Unit | object with `check_freshness` → returned; object without → `None` |
| `test_freshness_check_to_dict_is_json_serializable` | same | Unit | `json.dumps(check.to_dict())` succeeds; enum values are strings |

## Success criteria

- [ ] All symbols above exist with the listed types and defaults.
- [ ] No existing call sites change behaviour in this subtask (pure addition).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Frozen dataclasses, full annotations, `from __future__ import annotations` (house style).
- No I/O in `models.py` or `compare_periods`.
- See [CLAUDE.md](/CLAUDE.md) § "Conventions worth knowing" and
  [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- HTTP probing - [02](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/02-conditional-http-probe.md).
- Implementing probes on providers - [03](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/03-provider-freshness-probes.md).
