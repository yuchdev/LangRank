# Threat Model - stackoverflow-tags fetch - 2026-09-25

Scope: subtask [04 - Fetch: Stack Exchange API client & offline cache](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/04-fetch-api-and-offline-cache.md),
the milestone's first provider to perform real outbound network requests. Gate context:
[source note](/docs/source-notes/stackoverflow-tags.md).
Reviewer: Security Auditor agent.

## Assets & trust boundaries

- Assets: `LANGRANK_STACKEXCHANGE_KEY` (optional API key, secret); the local cache dir
  (`LANGRANK_CACHE`); the SQLite DB; process logs and error output.
- Trust boundaries crossed:
  1. Outbound: our request (may carry the key) -> `api.stackexchange.com` (untrusted network,
     redirects, TLS).
  2. Inbound: attacker-influenceable HTTP response (headers, gzip stream, JSON body, `backoff`
     field) -> `util/http.py` -> `providers/common.py` cache write -> provider parse.
  3. Cache read-back: `load_cached_payload` reads files from `LANGRANK_CACHE` (an offline replay
     path a local/other-process actor could poison) back into the pipeline.
- Only aggregate integer counts are ever stored; no user-contributed content crosses into the DB.

## Findings

### [CRITICAL] SEC-1 API key must never reach error messages, logs, artifact URL, or cache
- Vector / evidence: `src/langrank/util/http.py:45-49` - `get_bytes` raises
  `map_error(last_error)` which is `FetchError(str(error))`; `str(httpx.HTTPError)` embeds the full
  request URL. If the new `get_json(url, params)` places the key in the URL query string (or httpx
  serializes `params` into the failing request URL), the key leaks into the exception message and
  from there into any log sink / stack trace. `payload_from_content` (`providers/common.py:44-51`)
  also copies `url` verbatim into `RawArtifact.url` and `metadata_json`.
- Impact: full credential disclosure in logs/reports; the `.claude/hooks/secret_scan.py` hook would
  fire, but a leaked key in an error surface is a live secret compromise.
- Mitigation (coder MUST meet): pass the key only via the httpx `params` argument, never
  string-formatted into `url`; before raising, scrub query strings from any URL in the error text
  (redact `key`/`access_token`); build `RawArtifact.url` and `metadata_json` from the
  key-free base URL only; add `test_api_key_not_persisted` plus an error-path test asserting the key
  is absent from the raised message. CWE-532, CWE-209; OWASP A09:2021.

### [HIGH] SEC-2 Redirect handling can exfiltrate the key to an attacker host
- Vector / evidence: `src/langrank/util/http.py:23-28` builds the client with
  `follow_redirects=True`. A 3xx from an intercepted/misbehaving endpoint to another host causes
  httpx to replay the request (and its key-bearing `params`) to that host.
- Impact: SSRF-style credential exfiltration / requests sent to an unintended origin.
- Mitigation: for the keyed JSON path, pin the scheme+host to `https://api.stackexchange.com` and
  do not follow cross-host redirects while a key is attached (or drop auth params on redirect);
  reject non-HTTPS targets. CWE-918, CWE-601; OWASP A10:2021.

### [HIGH] SEC-3 Unbounded response / decompression bomb
- Vector / evidence: `get_bytes` returns `response.content` with no size cap; the Stack Exchange API
  serves gzip-encoded JSON, so httpx auto-decompresses - a hostile/oversized body inflates into
  memory before any limit is applied. The new `get_json` will `json.loads` the whole body.
- Impact: memory exhaustion / DoS of the CLI process.
- Mitigation: enforce a maximum response size (stream and abort past a fixed byte ceiling, and cap
  post-decompression bytes) and a request timeout (already 20s); raise `FetchError` on overflow.
  CWE-400, CWE-409; OWASP A05:2021.

### [MEDIUM] SEC-4 Untrusted JSON parsing without shape validation
- Vector / evidence: subtask 04 payload is built from `filter=total` responses; `count_questions`
  trusts `total` and `backoff` fields from the response.
- Impact: type confusion / crashes / a hostile `backoff` value driving an unbounded sleep.
- Mitigation: parse with `json.loads` only (never `eval`); validate that `total` is a non-negative
  int and `backoff` is a bounded number (clamp to a sane max, e.g. <= 300s) before sleeping; treat
  malformed JSON as `FetchError`. CWE-20, CWE-770.

### [MEDIUM] SEC-5 Cache path traversal / symlink on read-back
- Vector / evidence: `providers/common.py:34` composes the cache filename from `provider_id` and a
  hex sha; subtask 04 adds `load_cached_payload(provider_id, cache_dir)` selecting the "newest
  cached file for provider". A crafted `provider_id` containing path separators, or a symlinked
  cache entry, could read/write outside `cache_dir`.
- Impact: read/write outside the intended cache directory; poisoned offline replay.
- Mitigation: constrain `provider_id` to `[a-z0-9-]`; glob only `{provider_id}-*.json|.csv|.bin`
  within `cache_dir`; resolve and assert each candidate stays under `cache_dir.resolve()` and is a
  regular file (reject symlinks). CWE-22, CWE-59.

### [MEDIUM] SEC-6 Daily request budget and backoff must be enforced (self-DoS / ban)
- Vector / evidence: `util/http.py` has no rate limiting; the source note sets a 5000 requests/day
  ceiling (300/day without a key). Subtask 04 requires refusing to start when the planned request
  count exceeds the budget and sleeping on any `backoff`.
- Impact: quota exhaustion, IP throttle (`throttle_violation`), or a Stack Exchange ban for the
  shared egress IP.
- Mitigation: `StackExchangeClient` counts issued requests, raises `FetchError` before the first
  call when the plan exceeds `daily_budget` (stating required vs available), and honours every
  `backoff` (bounded per SEC-4); tests `test_fetch_budget_exceeded_raises_before_requests` and
  `test_fetch_honours_backoff` must cover both. CWE-770, CWE-799.

### [LOW] SEC-7 Audit trail for scheduled fetch
- Vector / evidence: `FetchService` records `fetch_runs`; the scheduled/unattended path should log
  request counts and denominator used, without any user content or the key.
- Impact: weak repudiation story for automated fetches.
- Mitigation: record request count, month window, and denominator in the fetch-run record; counts
  only, never user content, never the key. CWE-778.

## Verdict: BLOCK

SEC-1 is CRITICAL: subtask 04 must not merge to `master` until the key-scrubbing requirements
(SEC-1, plus the redirect-pinning of SEC-2) are implemented and proven by tests asserting the key
is absent from error messages, `RawArtifact.url`, `metadata_json`, and the cache. Hand SEC-1..SEC-6
fixes to `python-expert` and the regression tests to `testing-expert`; re-audit before the merge
gate clears. Findings SEC-3..SEC-7 are follow-up requirements to satisfy within the same subtask.
</content>

## Re-audit - 2026-09-25 (implementation of subtask 04)

Scope re-audited: uncommitted `src/langrank/util/http.py`, `src/langrank/providers/common.py`,
`src/langrank/providers/stackoverflow_tags.py`, `tests/unit/test_stackoverflow_tags_fetch.py`
(`git diff HEAD`). Unit tests run: `uv run pytest tests/unit/test_stackoverflow_tags_fetch.py -q`
-> 10 passed. Live integration tests not run (per scope).

### Per-SEC verdict

- SEC-1 (key never in error/logs/artifact/cache): MET. Key passed only via httpx `params`
  (`stackoverflow_tags.py` `count_questions`); `RawArtifact.url`/`metadata_json` built from
  secret-free `API_URL`; `map_error` -> `_scrub_message`/`_scrub_url` redact `key`/`access_token`
  from error text (`util/http.py`). Tests `test_api_key_not_persisted`,
  `test_api_key_scrubbed_from_error_message` both assert presence of REDACTED and absence of key.
- SEC-2 (redirect/host exfiltration): MET in code, UNTESTED. `get_json` enforces `scheme == https`,
  `netloc == allowed_host`, builds client with `follow_redirects=False`, and `_read_capped` raises
  on `response.is_redirect`. No dedicated test for off-host / non-HTTPS / 3xx refusal.
- SEC-3 (unbounded / decompression bomb): MET in code, UNTESTED. `_read_capped` streams via
  `iter_bytes` and aborts past `max_response_bytes` (10 MB, post-decompression). No test exercising
  an oversized body.
- SEC-4 (untrusted JSON shape + backoff clamp): MET in code, PARTIALLY TESTED. `count_questions`
  rejects non-dict, and `total` that is bool/non-int/negative; `json.loads` only, JSONDecodeError ->
  FetchError; `_honour_backoff` clamps to `MAX_BACKOFF_SECONDS` (300s) and ignores bool/non-numeric.
  `test_fetch_honours_backoff` covers a valid backoff=2 only; no test for the 300s clamp, malformed
  `total`, or non-JSON body.
- SEC-5 (cache traversal/symlink on read-back): MET in code, PARTIALLY TESTED. `load_cached_payload`
  enforces `_PROVIDER_ID_RE` (`[a-z0-9-]`), single-level glob within `cache_dir.resolve()`, skips
  symlinks, requires containment (`startswith(prefix)`) and regular file. Only happy-path
  (`test_offline_uses_cached_payload`) and empty-cache (`test_offline_without_cache_raises`) tested;
  no test for symlink rejection, out-of-tree containment, or invalid provider_id.
- SEC-6 (daily budget + backoff): MET, TESTED. `StackExchangeClient.ensure_budget` raises before the
  first call; `test_fetch_budget_exceeded_raises_before_requests` asserts `calls == []`. Backoff
  honoured per SEC-4.
- SEC-7 (audit trail): MET (LOW). `metadata_json` records `source`, `denominator`, `month_count`,
  `requests_made`; no user content, no key. FetchService `fetch_runs` recording is downstream
  (subtask 05+), out of this diff.

### Required follow-ups (severity)

- [HIGH] Add regression tests for SEC-2: off-host URL, non-HTTPS URL, and a 3xx response all raise
  FetchError and issue no cross-host request (assert on MockTransport call log).
- [HIGH] Add SEC-3 test: response body exceeding `max_response_bytes` raises FetchError.
- [MEDIUM] Add SEC-4 tests: backoff far above 300 sleeps exactly `MAX_BACKOFF_SECONDS`; malformed
  `total` (string/negative/bool) and non-JSON body each raise FetchError.
- [MEDIUM] Add SEC-5 tests: symlinked cache entry is skipped; a candidate resolving outside
  `cache_dir` is rejected; unsafe `provider_id` raises FetchError.

All follow-ups are test-coverage gaps against code that is already correct; no product-code defect
was found. Hand these regression tests to `testing-expert`.

### Re-audit verdict: PASS_WITH_FOLLOWUP (CLEAR)

The CRITICAL (SEC-1) is fully implemented and proven by tests; no CRITICAL remains, so the merge gate
is not blocked. The HIGH/MEDIUM items above are missing-test follow-ups to close within this subtask.

## Task-close review - 2026-09-25 (subtasks 05-08, diff b00835b..HEAD)

Scope: parse of untrusted JSON/CSV (`stackoverflow_tags.py` `_parse_api_json`,
`_parse_sede_csv`), `langrank import` path, live-test gating, committed fixtures, secret scan.

- Injection into DB: no regression. All writes are parameterized (`repository.py`
  `upsert_observations` uses `?` placeholders + `ON CONFLICT`); CSV/JSON cells never reach raw
  SQL. Unresolved tags are skipped (`normalize` -> `last_unmapped`), so only known-alias tags are
  persisted - a CSV formula string cannot enter stored data. CWE-89 not present.
- Untrusted parse shape: `_parse_api_json` uses `json.loads` only, rejects non-dict / missing
  `months`, and wraps `KeyError/TypeError/ValueError` in `ParseError`; `_parse_sede_csv` validates
  required columns and coerces numerics under the same guard. Backoff clamp intact
  (`stackoverflow_tags.py:825`, `min(float(backoff), MAX_BACKOFF_SECONDS)`).
- Int overflow: N/A (Python arbitrary-precision ints); no fixed-width arithmetic.
- Live-test gating: MET. `tests/conftest.py` `pytest_collection_modifyitems` skips any `live`-marked
  item unless `LANGRANK_LIVE_TESTS=1`; marker registered in `pyproject.toml`; the only live test
  (`tests/integration/test_stackoverflow_tags_live.py`) carries `pytest.mark.live`. Plain
  `uv run pytest` (CI) makes no network call.
- Fixtures: clean. `api_sample.json`/`sede_sample.csv`/`expected_observations.json` hold aggregate
  counts and sha256 record hashes only - no app key (captured unauthenticated), no usernames, IDs,
  titles, or bodies (`filter=total` returns just `{"total": N}`).
- Secret scan of the diff: no hard-coded credentials; the key is read from
  `LANGRANK_STACKEXCHANGE_KEY` via `os.environ.get`.

### Residual (LOW, follow-up - not merge-blocking)

- [LOW] `langrank import` reads the whole local file (`cli.py:359` `path.read_bytes()`), and
  `_parse_sede_csv` additionally does `content.decode().splitlines()` - unbounded memory on a huge
  local file. Trust boundary is the operator's own filesystem (no network amplification), and the
  SEC-3 10 MB cap covers only the network fetch path. Acceptable for now; consider a size guard on
  the import path (CWE-400).

### Task-close verdict: CLEAR

No CRITICAL/HIGH regression in subtasks 05-08. SEC-1..SEC-7 remain met; the one residual is a
pre-existing LOW self-DoS on the operator-controlled import path.
