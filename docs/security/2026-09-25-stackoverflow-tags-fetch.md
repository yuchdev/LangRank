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
