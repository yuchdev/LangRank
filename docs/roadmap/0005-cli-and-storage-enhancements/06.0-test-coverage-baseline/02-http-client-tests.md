# Subtask 06.0/02 - HTTP client tests

**Task:** [06.0 - Test Coverage Baseline](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md) ·
**Role:** Testing Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Cover `src/langrank/util/http.py` (0% today) with mocked-transport tests, so the HTTP layer that
milestones 0001/0004 will build on is pinned before they change it.

## Baseline

- `HttpClientOptions(timeout=20.0, user_agent="langrank/0.1.0", retries=3, backoff_seconds=0.5)`.
- `HttpClientFactory.build() -> httpx.Client` (sets `User-Agent`, `follow_redirects=True`).
- `get_bytes(url) -> bytes` retries `{429, 500, 502, 503, 504}` and `httpx.HTTPError` up to
  `retries` times with `sleep(backoff_seconds * 2**attempt)`, then raises `FetchError`.
- `map_error(error) -> FetchError(str(error))`.
- No provider calls it yet (all read bundled CSVs from `src/langrank/providers/data/`).

## Files

| Action | Path                          | Purpose |
|--------|-------------------------------|---------|
| Create | `tests/unit/test_http.py`     | Tests below |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `mock_factory` | pytest fixture | `(handler: Callable[[httpx.Request], httpx.Response]) -> HttpClientFactory` | - | `build()` takes no transport, so monkeypatch `HttpClientFactory.build` to return `httpx.Client(transport=httpx.MockTransport(handler), headers=...)`; also monkeypatch `langrank.util.http.sleep` to a no-op recorder (no `src/` change) |

## Behaviour & validators

1. A 200 response returns the body bytes unchanged.
2. A non-retryable 4xx (404) raises `FetchError` (a `LangRankError`) after `retries` attempts, never a raw `httpx` exception.
3. A retryable status (503) followed by 200 returns the body; `sleep` was called with `0.5`.
4. Persistent 429 raises `FetchError` whose message contains `temporary upstream status 429`; backoff sequence is `[0.5, 1.0]`.
5. `map_error(httpx.ConnectTimeout("boom"))` returns a `FetchError` with message `boom`.
6. Configured user agent is sent.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_get_bytes_returns_body` | `tests/unit/test_http.py` | Mock | rule 1 |
| `test_get_bytes_404_raises_fetch_error` | `tests/unit/test_http.py` | Mock | rule 2 |
| `test_get_bytes_retries_then_succeeds` | `tests/unit/test_http.py` | Mock | rule 3 |
| `test_get_bytes_persistent_429_backoff_sequence` | `tests/unit/test_http.py` | Mock | rule 4 |
| `test_map_error_wraps_message` | `tests/unit/test_http.py` | Unit | rule 5 |
| `test_build_sets_user_agent` | `tests/unit/test_http.py` | Mock | rule 6 |

## Success criteria

- [ ] `src/langrank/util/http.py` coverage ≥ 90%.
- [ ] No test performs a real network call.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Mocked only; no `@pytest.mark.integration` tests here.

## Out of scope

- Conditional requests (ETag/Last-Modified) - [0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md).
