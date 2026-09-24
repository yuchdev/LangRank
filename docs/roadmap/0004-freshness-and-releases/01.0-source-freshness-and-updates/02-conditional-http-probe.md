# Subtask 01.0/02 - Conditional HTTP Probe & Artifact Validators

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Give `HttpClientFactory` a cheap, conditional "has this URL changed?" probe that never
downloads a body, make the client injectable with an `httpx` transport for tests, and let
`payload_from_content` record the `ETag`/`Last-Modified` validators that `raw_artifacts`
already has columns for.

## Baseline

- `util/http.py:HttpClientFactory.get_bytes` does GET with retry/backoff; unused today.
- `HttpClientOptions` has `timeout`, `user_agent`, `retries`, `backoff_seconds` - no
  transport injection.
- `providers/common.py:payload_from_content` builds `RawArtifact` with
  `http_etag`/`http_last_modified` left `None`.
- `Database.record_raw_artifact` already persists both fields.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/util/http.py` | `HttpProbeResult`, `HttpClientFactory.probe()`, `HttpClientOptions.transport`, `user_agent` from `__version__` |
| Modify | `src/langrank/providers/common.py` | `payload_from_content(..., http_etag=None, http_last_modified=None)` |
| Modify | `src/langrank/db/repository.py` | `Database.latest_raw_artifact(rating_id) -> sqlite3.Row \| None` |
| Create | `tests/unit/test_http_probe.py` | MockTransport-driven probe tests |
| Modify | `tests/unit/test_freshness_model.py` or create `tests/unit/test_raw_artifact_validators.py` | payload/DB round-trip of validators |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `HttpClientOptions.transport` | field | `httpx.BaseTransport \| None` | `None` | Passed to `httpx.Client(transport=...)` |
| `HttpClientOptions.user_agent` | field | `str` | `f"langrank/{__version__}"` | Replaces hardcoded `"langrank/0.1.0"` |
| `HttpProbeResult` | frozen dataclass | `status_code: int`, `not_modified: bool`, `etag: str \| None`, `last_modified: str \| None`, `method: str` | - | `method` is `"HEAD"` or `"GET"` |
| `HttpClientFactory.probe` | method | `(url: str, *, etag: str \| None = None, last_modified: str \| None = None) -> HttpProbeResult` | - | Conditional request |
| `payload_from_content` | function | new kw-only `http_etag: str \| None = None`, `http_last_modified: str \| None = None` | `None` | Copied onto `RawArtifact` |
| `Database.latest_raw_artifact` | method | `(rating_id: str) -> sqlite3.Row \| None` | - | Newest by `retrieved_at` |

## Behaviour & validators

1. `probe` sends `HEAD` with `If-None-Match: <etag>` and/or `If-Modified-Since:
   <last_modified>` when supplied.
2. `304` → `not_modified=True`. `2xx` → `not_modified=False` with echoed validators.
3. If the server answers `HEAD` with `405`/`501`, retry **once** as `GET` using
   `client.stream(...)` with the same conditional headers and close the response without
   reading the body (`response.close()` before any `.read()`); `method="GET"`.
4. Transient statuses (`429`, `5xx`) reuse the existing retry/backoff loop; final failure
   raises `FetchError` (mapped via `map_error`).
5. `probe` never reads more than headers - enforced by a test whose MockTransport handler
   fails if a body is consumed (stream wrapper that raises on iteration).
6. `latest_raw_artifact` orders by `retrieved_at DESC, id DESC` for determinism.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_probe_sends_conditional_headers` | `tests/unit/test_http_probe.py` | Mock | request carries `If-None-Match` / `If-Modified-Since` |
| `test_probe_304_is_not_modified` | same | Mock | `not_modified is True`, `method == "HEAD"` |
| `test_probe_200_returns_validators` | same | Mock | `etag`, `last_modified` echoed |
| `test_probe_falls_back_to_get_on_405_without_reading_body` | same | Mock | second request is `GET`; body stream never iterated |
| `test_probe_retries_transient_then_raises_fetch_error` | same | Mock | 3× `503` → `FetchError`; `backoff_seconds=0` in test |
| `test_payload_from_content_records_http_validators` | `tests/unit/test_raw_artifact_validators.py` | Unit | artifact fields set; `Database.latest_raw_artifact` returns them after `record_raw_artifact` |

## Success criteria

- [ ] `probe` implemented with HEAD→GET fallback and no body reads.
- [ ] Validators persisted end-to-end when a provider passes them.
- [ ] No test performs real network I/O.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `util/http.py` stays provider-agnostic; no provider IDs in it.
- Providers remain the only callers of network code inside `fetch()`/`check_freshness()` -
  see [CLAUDE.md](/CLAUDE.md).

## Out of scope

- Changing any provider's `fetch()` to go live (milestone 0001).
