# Subtask 01.0/04 - Fetch: Stack Exchange API client, SEDE import & offline cache

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Implement `fetch()` for the `api` source (monthly `filter=total` counts per master tag plus
an all-questions denominator) and a shared offline cache reader, so `--offline` replays the
last cached artifact without network.

## Baseline

- `util/http.py:HttpClientFactory.get_bytes` - retries on 429/5xx, no query-param or JSON
  helpers, no rate limiting.
- `providers/common.py:payload_from_content` - writes `{provider}-{sha12}.{ext}` into the
  provider cache dir; `ext` is only `.csv` or `.bin`.
- `FetchRequest.since/until/years/offline/refresh/no_cache/source` exist.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/stackoverflow_tags.py` | `fetch()`, `_month_windows()`, `StackExchangeClient` |
| Modify | `src/langrank/providers/common.py` | `load_cached_payload()`; `.json` extension support |
| Modify | `src/langrank/util/http.py` | `get_json(url, params)` helper |
| Create | `tests/unit/test_stackoverflow_tags_fetch.py` | Mocked-transport tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `HttpClientFactory.get_json` | method | `(url: str, params: dict[str, str] \| None = None) -> Any` | - | Reuses retry loop |
| `load_cached_payload` | function | `(*, provider_id: str, cache_dir: Path) -> FetchPayload` | - | Newest cached file for provider; `FetchError` if none |
| `StackExchangeClient` | class | `(http: HttpClientFactory, key: str \| None, daily_budget: int)` | budget from source note | Counts requests, honours `backoff` seconds |
| `StackExchangeClient.count_questions` | method | `(tag: str \| None, start: date, end: date) -> int` | - | `/2.3/questions?site=stackoverflow&filter=total` |
| `_month_windows` | function | `(since: date, until: date) -> list[tuple[date, date]]` | - | Excludes the current incomplete month |
| `STACKEXCHANGE_KEY_ENV` | const | `str` | `"LANGRANK_STACKEXCHANGE_KEY"` | Optional |

Payload format (JSON, one artifact per fetch):
`{"source": "api", "denominator": "all_questions", "months": [{"month": "2024-01", "total": 123, "tags": {"python": 456, ...}}]}`

## Behaviour & validators

1. `request.source in {None, "auto", "api"}` → API mode; `"sede"` → `ProviderError`
   telling the user to use `langrank import --rating stackoverflow-tags <csv>`; anything
   else → `ProviderError` listing valid sources.
2. Default window: last 10 years ending at the last complete month; `since/until/years`
   narrow it.
3. `request.offline` → `load_cached_payload`; no `httpx` client is constructed.
4. When the request budget would be exceeded, raise `FetchError` **before** the first call,
   stating required vs. available requests (no partial silent fetch).
5. A `backoff` field in any response sleeps that many seconds before the next call.
6. The API key, if present, is sent as a query param but **never** written to
   `RawArtifact.url`, `metadata_json`, or error messages.
7. `payload_from_content(..., mime_type="application/json")` writes a `.json` file.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_month_windows_excludes_current_month` | `tests/unit/test_stackoverflow_tags_fetch.py` | Unit | Window list ends at previous month |
| `test_fetch_api_builds_payload_from_mocked_transport` | `tests/unit/test_stackoverflow_tags_fetch.py` | Mock | `httpx.MockTransport`; payload JSON has totals per tag |
| `test_fetch_budget_exceeded_raises_before_requests` | `tests/unit/test_stackoverflow_tags_fetch.py` | Mock | Zero requests issued, `FetchError` |
| `test_fetch_honours_backoff` | `tests/unit/test_stackoverflow_tags_fetch.py` | Mock | `sleep` patched and called with backoff value |
| `test_api_key_not_persisted` | `tests/unit/test_stackoverflow_tags_fetch.py` | Mock | Key absent from artifact url/metadata |
| `test_offline_uses_cached_payload` | `tests/unit/test_stackoverflow_tags_fetch.py` | Unit | No transport call; same bytes returned |
| `test_offline_without_cache_raises` | `tests/unit/test_stackoverflow_tags_fetch.py` | Unit | `FetchError` |
| `test_stackoverflow_tags_live_smoke` | `tests/integration/test_stackoverflow_tags_live.py` | Integration | `@pytest.mark.integration`; one tag, one month |

## Success criteria

- [ ] `langrank fetch stackoverflow-tags --since 2025-01 --until 2025-02` works live.
- [ ] `--offline` replays the cache with no network.
- [ ] Tests above pass; lint/format/mypy/pytest green.

## Constraints

- Network only inside `fetch()`; parse/normalize operate on bytes.
- Unattended/scheduled fetch stays disabled unless subtask 01's gate verdict allows it.
- Secrets never logged (see `.claude/hooks/secret_scan.py`).

## Out of scope

- SEDE CSV parsing (subtask 05); ETag/Last-Modified freshness (Milestone 0004 Task 01.0).
