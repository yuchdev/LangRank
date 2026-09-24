# Subtask 03.0/03 - Streaming Download to Cache

**Task:** [03.0 - Large-Source Performance Hardening](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Large artifacts (survey ZIPs, data dumps) are streamed straight to the cache directory while
their sha256 is computed incrementally, and handed to providers as a path-backed
`FetchPayload` - never held in memory as a single `bytes` object.

## Baseline

- `src/langrank/util/http.py:HttpClientFactory.get_bytes(url) -> bytes` - retries on
  429/5xx with exponential backoff; returns `response.content`.
- `src/langrank/providers/common.py:payload_from_content(...)` - hashes full `bytes`, writes
  `cache_dir/<provider>-<sha12><ext>`, builds `RawArtifact`.
- `src/langrank/providers/base.py:FetchPayload(artifact: RawArtifact | None, content: bytes)`.
- `RawArtifact.http_etag` / `http_last_modified` exist but are never populated.

## Files

| Action | Path                                     | Purpose |
|--------|------------------------------------------|---------|
| Modify | `src/langrank/util/http.py`              | `download_to()` streaming method |
| Modify | `src/langrank/providers/base.py`         | `FetchPayload.content_path`; lazy `content` access helper |
| Modify | `src/langrank/providers/common.py`       | `payload_from_download()` |
| Create | `tests/unit/test_streaming_download.py`  | `httpx.MockTransport`-based tests |

## Symbols / fields

| Symbol                              | Kind      | Type / signature                                                                       | Default | Notes |
|-------------------------------------|-----------|----------------------------------------------------------------------------------------|---------|-------|
| `DownloadResult`                    | dataclass | frozen: `path: Path`, `sha256: str`, `size: int`, `etag: str \| None`, `last_modified: str \| None`, `mime_type: str` | - | In `util/http.py` |
| `HttpClientFactory.download_to`     | method    | `(url: str, destination_dir: Path, *, chunk_size: int = 1 << 20) -> DownloadResult`     | 1 MiB   | Writes `*.part`, renames atomically to `<sha12><ext>` on success |
| `HttpClientOptions.transport`       | field     | `httpx.BaseTransport \| None`                                                          | `None`  | Test injection point |
| `FetchPayload.content_path`         | field     | `Path \| None`                                                                         | `None`  | Additive (minor API change) |
| `FetchPayload.content`              | field     | `bytes`                                                                                | `b""` when path-backed | Kept for compatibility |
| `open_payload_text`                 | function  | `(payload: FetchPayload, encoding: str = "utf-8") -> TextIO` (context manager)          | -       | In `providers/common.py`; opens path or wraps bytes |
| `payload_from_download`             | function  | `(*, provider_id, download: DownloadResult, url, metadata_json, no_cache) -> FetchPayload` | - | Populates `http_etag`/`http_last_modified` |

## Behaviour & validators

1. `download_to` uses `client.stream("GET", url)` + `iter_bytes(chunk_size)`; sha256 updated per chunk.
2. Retry semantics identical to `get_bytes` (same status set, same backoff); a partial `.part`
   file is deleted before each retry and on final failure.
3. Rename is atomic (`Path.replace`) so an interrupted download never leaves a file that looks complete.
4. If a file with the same sha256 name already exists, it is kept and `.part` is discarded (dedup).
5. `no_cache=True`: the provider uses `get_bytes` (in-memory, as today) instead of
   `download_to`. A path-backed payload has to outlive `fetch()`, so a temp-dir download would
   need lifecycle handling in `FetchService`, which is not worth it for an opt-out flag.
   `--no-cache` is documented as unsuitable for very large sources.
6. `ETag`/`Last-Modified` response headers are recorded on `RawArtifact` (groundwork for
   [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates)).
7. `open_payload_text` on a bytes payload behaves exactly like today's `content.decode()`.

## Tests

| Test function                                     | File                                    | Type | Asserts |
|---------------------------------------------------|-----------------------------------------|------|---------|
| `test_download_streams_and_hashes`                | `tests/unit/test_streaming_download.py` | Mock | 5 MiB mocked body → sha256 matches `hashlib` of body; file exists |
| `test_download_retries_then_succeeds`             | `tests/unit/test_streaming_download.py` | Mock | 503 then 200 → success, no leftover `.part` |
| `test_download_failure_leaves_no_partial_file`    | `tests/unit/test_streaming_download.py` | Mock | Always 503 → `FetchError`, directory has no files |
| `test_download_records_etag_and_last_modified`    | `tests/unit/test_streaming_download.py` | Mock | Headers land on `RawArtifact` |
| `test_open_payload_text_bytes_and_path_equivalent`| `tests/unit/test_streaming_download.py` | Unit | Same text from both payload kinds |
| `test_download_memory_is_bounded`                 | `tests/benchmarks/test_pipeline_benchmark.py` | Integration (`benchmark`) | 200 MiB streamed body → `tracemalloc` peak < 32 MiB |

## Success criteria

- [ ] No `response.content` use in the streaming path (`grep` in `download_to`).
- [ ] Existing providers unchanged and green (compatibility of `FetchPayload`).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Network only inside provider `fetch()` → `HttpClientFactory`; tests use `httpx.MockTransport`, never the network.
- Respect source terms: this subtask adds no automatic fetching.

## Out of scope

- Conditional requests (`If-None-Match`) - Milestone 0004. Retention policy - [Milestone 0004 Task 03.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-030---source-archival-strategy).
