# Threat Model - github fetch - 2026-09-25

Scope: subtask [05 - Innovation Graph fetch & parse](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/05-innovation-graph-fetch-and-parse.md)
(the milestone's second real outbound network source) and subtask
[07 - Octoverse annual rankings dataset](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/07-octoverse-annual-rankings.md)
(offline, curated CSV). Gate context: [source note](/docs/source-notes/github.md).
Reviewer: Security Auditor agent.

This model **reuses** the Stack Overflow Tags model
([docs/security/2026-09-25-stackoverflow-tags-fetch.md](/docs/security/2026-09-25-stackoverflow-tags-fetch.md))
and does not restate it. The shared helpers already exist and their SEC-1..SEC-7 mitigations still
apply: `HttpClientFactory.get_json` (HTTPS + `allowed_host` pin, `follow_redirects=False`,
post-decompression size cap, `_scrub_message`/`_scrub_url` redaction) and `common.load_cached_payload`
(provider-id allowlist, single-level glob under `cache_dir.resolve()`, symlink/containment checks).
Below are only the **new** exposures the GitHub variant introduces.

## Assets & trust boundaries

- Assets: optional `GITHUB_TOKEN` (a secret; a personal access token can carry broad scopes and a
  5000/h quota); the local cache dir (`LANGRANK_CACHE`); the SQLite DB; process logs/error output.
- New trust boundaries:
  1. Outbound to **two** distinct hosts: `api.github.com` (commits API, the only request that may
     carry the token) and `raw.githubusercontent.com` (raw CSV download; must never carry the token).
  2. Inbound: the commits-API JSON body yields a commit `sha` that is interpolated **into the raw
     download URL path** - an untrusted value crossing into a URL.
  3. Inbound: a large, attacker-influenceable CSV body -> parse -> normalize.
  4. Octoverse: a repo-committed curated CSV (`providers/data/github_octoverse.csv`), trusted via
     code review, no network.
- Only aggregate integer pusher counts and published ranks are stored; no user content.

## Findings

### [HIGH] GH-SEC-1 GITHUB_TOKEN must be header-only and is NOT covered by the existing scrubber
- Vector / evidence: the token is sent via an `Authorization: Bearer <token>` header on the
  `api.github.com` commits request. `_scrub_message`/`_scrub_url` (`src/langrank/util/http.py`) only
  redact `key`/`access_token` **query parameters inside URLs** - they do not touch request/response
  **headers**. `get_json` currently exposes no header-passing argument at all, so subtask 05 must add
  one; any code path that stringifies the request (`httpx.Request` repr, a debug log, an
  `httpx.HTTPError` that embeds headers) would leak the bearer token past the scrubber.
- Impact: disclosure of a live GitHub credential in logs/reports (CWE-532, CWE-209; OWASP A09:2021).
- Mitigation (implementer MUST meet): read the token only from `os.environ.get("GITHUB_TOKEN")`;
  pass it only as an `Authorization` header, only on the `api.github.com` request, never in a URL,
  never into `RawArtifact.url`/`metadata_json`/cache; extend the scrubber to also redact an
  `Authorization`/`authorization` header value (and any `Bearer <...>` / `token <...>` substring) in
  error and log text; add tests asserting the token is absent from the raised message, the artifact,
  and the cache, and that no token is attached to the raw request.

### [HIGH] GH-SEC-2 Untrusted commit SHA interpolated into the raw URL path
- Vector / evidence: `_resolve_commit_sha` parses `sha` from the commits-API JSON and
  `IG_RAW_URL = ".../github/innovationgraph/{sha}/data/languages.csv"` interpolates it. A malformed
  or hostile `sha` (e.g. containing `../`, `@`, or a full URL) injected into the path could redirect
  the download to another path/ref, or (with `raw` accepting `refs/`) an attacker-chosen file.
- Impact: path/ref confusion / SSRF-within-host, poisoned reproducible anchor (CWE-20, CWE-918,
  CWE-88).
- Mitigation: validate `sha` against `^[0-9a-f]{40}$` before interpolation; reject otherwise with
  `FetchError`; build the raw URL only from the validated SHA.

### [HIGH] GH-SEC-3 Raw CSV path must be host-pinned, no-redirect, and size-capped
- Vector / evidence: the raw download is the natural fit for `get_bytes`, but `get_bytes`
  (`src/langrank/util/http.py`) builds its client with `follow_redirects=True`, applies **no
  `allowed_host` pin**, and returns `response.content` with **no size cap** - none of SEC-2/SEC-3's
  protections cover it. `languages.csv` is large and grows every quarter.
- Impact: cross-host redirect (token exfiltration if a token were ever attached; SSRF), and
  unbounded-memory DoS on an oversized/decompression-bomb body (CWE-400, CWE-601, CWE-918;
  OWASP A05/A10:2021).
- Mitigation: fetch the raw CSV through the hardened path (`get_json`'s capped/pinned/no-redirect
  read, generalized to return bytes, or an equivalent `get_bytes`-with-`allowed_host`+cap), pinning
  `allowed_host="raw.githubusercontent.com"`, `follow_redirects=False`, and a byte ceiling sized for
  the real file plus headroom; never attach the token to this host.

### [MEDIUM] GH-SEC-4 Pinned-commit integrity: record and re-check the CSV sha256
- Vector / evidence: the commit SHA gives content-addressed reproducibility upstream, but the bytes
  arriving over `raw.githubusercontent.com` are trusted only by TLS; a poisoned cache entry
  (`load_cached_payload` replay) or a substituted body would go undetected without a stored digest.
  `payload_from_content` already computes a sha256 for `RawArtifact`.
- Impact: silent use of a tampered/mismatched CSV; broken reproducibility (CWE-353, CWE-494).
- Mitigation: store the CSV sha256 in `RawArtifact`/artifact metadata alongside `commit_sha`; on
  offline/cache read-back, verify the cached bytes' sha256 and that `commit_sha` matches the sidecar
  before parsing; mismatch -> `FetchError`.

### [MEDIUM] GH-SEC-5 CSV parsing of untrusted input (shape + numeric validation)
- Vector / evidence: `_parse_innovation_graph(content, *, commit_sha)` parses the untrusted CSV.
  Required columns `num_pushers, language, iso2_code, year, quarter` must be validated; numeric
  fields must be coerced safely (`num_pushers` non-negative int, `year` plausible int,
  `quarter` in 1..4), and row count is unbounded.
- Impact: crashes/type confusion from malformed cells; a huge row count amplifying memory
  (CWE-20, CWE-1284, CWE-400).
- Mitigation: parse with the `csv` module (never `eval`); a missing required column -> `ParseError`
  naming it (already specified); wrap per-row `ValueError`/`KeyError` in `ParseError`; reject
  out-of-range `quarter`/negative counts; treat the SEC-3 size cap as the row-count bound. DB writes
  stay parameterized (`upsert_observations` uses `?` placeholders), so no SQL injection (CWE-89 N/A).

### [LOW] GH-SEC-6 Request budget & rate-limit handling
- Vector / evidence: commits API is 60/h unauthenticated (5000/h with token) and
  `raw.githubusercontent.com` throttles separately; the provider issues at most 2 requests per fetch.
- Impact: transient 403/429 rate-limit; negligible self-DoS given the tiny budget (CWE-770).
- Mitigation: enforce a ≤2-requests-per-fetch expectation; honour `Retry-After`/`X-RateLimit-Reset`
  and treat 403 rate-limit as a retryable/`FetchError` (do not busy-retry); refuse to start if a plan
  would exceed the applicable hourly ceiling.

### [LOW] GH-SEC-7 CSV-formula injection is an export-time, not ingest-time, concern
- Vector / evidence: a hostile `language` cell could begin with `=`/`+`/`-`/`@`. It never reaches raw
  SQL (parameterized) and only known-alias languages are persisted; unmapped ones are skipped. The
  only spreadsheet risk is downstream `export csv`.
- Impact: formula injection if a stored string were later opened in a spreadsheet (CWE-1236).
- Mitigation: rely on alias-only persistence here; leave formula-neutralizing to the export path if
  ever needed. No action required in subtasks 05/07.

### [LOW] GH-SEC-8 Octoverse variant: offline curated CSV, chart extraction refused
- Vector / evidence: subtask 07 reads a repo-committed `providers/data/github_octoverse.csv`; no
  network. `--allow-chart-extraction` is not implemented and a `octoverse-chart` source must raise
  `ProviderError`.
- Impact: minimal - trust boundary is the operator's own reviewed CSV (CWE-20 on the same coercion
  path as GH-SEC-5).
- Mitigation: same numeric/column validation as GH-SEC-5 for the curated CSV; keep the chart-source
  `ProviderError` guard; integrity of the bundled file is assured by code review.

### [LOW] GH-SEC-9 Audit trail for scheduled fetch
- Vector / evidence: the scheduled `innovation-graph` path should record the pinned `commit_sha`,
  request count, and quarter window in the fetch-run record - never the token, never user content.
- Impact: weak repudiation story for automated fetches (CWE-778).
- Mitigation: record `commit_sha`, `requests_made`, and the quarter window in `metadata_json`/
  `fetch_runs`; counts only.

## Verdict: PASS_WITH_FOLLOWUP

No CRITICAL finding: by design the token is header-scoped and kept off the raw host, and no
implementation code exists yet to leak it. GH-SEC-1..GH-SEC-3 are HIGH requirements that subtask 05
MUST implement and prove with tests before it can merge to `master`; GH-SEC-4/GH-SEC-5 are MEDIUM
requirements within the same subtask. Hand GH-SEC-1..GH-SEC-5 code changes (including the scrubber
extension for the `Authorization` header, the 40-hex SHA validator, and the host-pinned/size-capped
raw-bytes path) to `python-expert`, and the regression tests to `testing-expert`; re-audit the
subtask-05 implementation before the merge gate clears. Should any HIGH remain unmet at
implementation time, escalate that finding to BLOCK.
</content>

---

## Re-audit - subtask 02.0/05 implementation - 2026-09-25

Scope re-audited: uncommitted `git diff HEAD` in `src/langrank/util/http.py`
(`get_capped_bytes`, `headers=` on `get_json`/`_read_capped`, `_AUTH_HEADER_RE`/`_BEARER_TOKEN_RE`
scrubbing), `src/langrank/providers/github.py` (`_fetch_innovation_graph`, `_resolve_commit_sha`,
`_validate_commit_sha`, `_parse_innovation_graph`, sidecar replay), and
`tests/unit/test_github_innovation_graph.py`. Unit tests only (65 passed: the github, http and
stackoverflow-tags suites). Live tests not run.

### Per-GH-SEC verdict

- GH-SEC-1 (token header-only, never persisted, scrubbed): PASS. Token read from `GITHUB_TOKEN`,
  sent only as `Authorization: Bearer` on `api.github.com`; `get_capped_bytes` raw call passes no
  headers. Scrubber extended (`_AUTH_HEADER_RE` + `_BEARER_TOKEN_RE`, both applied in `map_error`).
  Char class `[A-Za-z0-9._~+/=-]` includes `_`, so `ghp_`/`github_pat_` tokens are covered. Proven
  by `test_ig_token_only_on_api_host_and_never_persisted` and `test_scrub_message_redacts_*`.
- GH-SEC-2 (SHA validated before URL build): PASS. `_validate_commit_sha` (`^[0-9a-f]{40}$`) gates
  both the API-returned and sidecar SHAs before `IG_RAW_URL.format`. Proven by
  `test_validate_commit_sha_rejects_malformed` (incl. `../`, url, uppercase, non-hex) and
  `test_resolve_commit_sha_rejects_non_hex_from_api`.
- GH-SEC-3 (raw CSV host-pinned/no-redirect/capped): PASS. `get_capped_bytes` enforces HTTPS +
  exact `allowed_host` before any request, `follow_redirects=False`, `_read_capped` refuses
  `is_redirect` and caps bytes (`IG_MAX_CSV_BYTES`, 64 MB headroom). Proven by
  `test_get_capped_bytes_refuses_off_host`, `test_ig_fetch_refuses_raw_redirect`,
  `test_get_capped_bytes_rejects_oversized_body`.
- GH-SEC-4 (record + re-verify csv_sha256 + commit_sha on replay): PASS. `commit_sha`+`csv_sha256`
  in `metadata_json` and `.meta` sidecar; offline replay re-hashes cached bytes, matches sidecar,
  re-validates SHA. `.meta` excluded from `_CACHE_EXTENSIONS` so it is never served as the artifact.
  Proven by `test_ig_offline_uses_cache`, `test_ig_offline_detects_tampered_sidecar`,
  `test_ig_offline_without_sidecar_raises`. Residual (LOW): binding is bytes<->sidecar written
  together, not bytes<->upstream commit; an actor who owns the cache dir can rewrite both. Accepted.
- GH-SEC-5 (CSV shape/numeric validation): PASS. stdlib `csv.DictReader`, required-column check
  naming the missing column, int coercion with non-negative `num_pushers`, `quarter` in 1..4,
  plausible `year`, `ParseError`-wrapped rows, UTF-8 guard. Row count bounded by the SEC-3 cap.
  Proven by `test_ig_parse_missing_column_raises`, `test_ig_parse_rejects_malformed_cells`,
  `test_ig_parse_rejects_non_utf8`.
- GH-SEC-6 (request budget / rate-limit): PASS_WITH_FOLLOWUP. `_ensure_request_budget` guard and the
  exactly-two-requests path are tested. Fixed exponential backoff is used and server
  `Retry-After`/`X-RateLimit-Reset` are intentionally NOT honoured - acceptable and arguably safer
  than trusting an upstream-supplied delay. Caveat: 403 is NOT specially excluded from retry - it is
  raised by `raise_for_status` and caught by the generic `except (httpx.HTTPError, FetchError)`, so
  it is retried up to `retries` times like any HTTP error (the "403 not retried" claim is not borne
  out by the code); request volume stays bounded by `retries` x 2, so no unbounded self-DoS.
- GH-SEC-7 (CSV formula injection = export-time): PASS. No change; ingest unaffected.
- GH-SEC-8 (Octoverse offline): N/A this subtask - Octoverse `fetch` still raises
  `NotImplementedError`; lands in subtask 07.
- GH-SEC-9 (audit trail): PASS_WITH_FOLLOWUP. `metadata_json` carries `commit_sha`,
  `requests_made`, `source_document_id`; the quarter window is applied in `parse` but not recorded
  in the artifact metadata, and no test asserts `requests_made`. `fetch_runs` recording is
  `FetchService` scope, out of this diff.

### Follow-ups (non-blocking)

- LOW GH-SEC-6: exclude non-retryable 4xx (401/403) from the retry loop so an auth/rate-limit 403
  fails fast instead of being retried `retries` times. Hand to `python-expert`.
- LOW GH-SEC-6: add a regression test asserting 429 -> bounded retry-with-backoff and 403 behaviour.
  Hand to `testing-expert`.
- LOW GH-SEC-9: record the quarter window in `metadata_json`/`fetch_runs`; add a test asserting
  `metadata_json["requests_made"] == 2`.
- INFO: `_BEARER_TOKEN_RE` can over-redact benign `token <8+ chars>` text - cosmetic only, no
  security impact; SO scrubbing regression suite still green.

No SEC-1 regression for Stack Overflow: shared `_scrub_message` only adds redactions; the reworded
messages ("upstream response body was not valid JSON", "refusing to follow cross-host redirect")
still satisfy the substring assertions in `tests/unit/test_http.py` and
`tests/unit/test_stackoverflow_tags_fetch.py`.

### Re-audit verdict: CLEAR (PASS)

All three HIGH items (GH-SEC-1/2/3) and both MEDIUM items (GH-SEC-4/5) are implemented and proven by
unit tests; no CRITICAL or HIGH finding remains. Remaining items are LOW follow-ups. The subtask-05
diff clears the merge gate.

---

## Task-close review - Task 02.0 (GitHub provider) - 2026-09-25

Scope: `git diff 47c01ab..HEAD` on `milestone/0001-new-rating-providers` (committed
GitHub provider, `util/http.py`, Octoverse CSV, fixtures, unit/contract tests). Unit +
contract tests only (77 passed); live tests not run. No product code edited.

### Re-confirmation vs the prior re-audit

- GH-SEC-1 (token header-only, scrubbed, never persisted): PASS, no regression.
  `_fetch_innovation_graph` reads `GITHUB_TOKEN`, attaches it only as an
  `Authorization: Bearer` header on the `api.github.com` commits call; the
  `raw.githubusercontent.com` `get_capped_bytes` call passes no headers
  (`github.py:485`). Proven by `test_github_innovation_graph.py:142-164` (token absent
  from raw URL, artifact url/local_path/metadata_json, content, and cache).
- GH-SEC-2 (40-hex SHA validated before URL build): PASS. `_validate_commit_sha`
  gates both API-returned and sidecar SHAs (`github.py:875-877, 901, 536`).
- GH-SEC-3 (raw CSV host-pinned/no-redirect/capped): PASS. `get_capped_bytes`
  enforces HTTPS + exact `allowed_host`, `follow_redirects=False`, redirect refusal
  and `IG_MAX_CSV_BYTES` ceiling (`http.py:206-282`).
- GH-SEC-4 (csv_sha256 + commit_sha recorded and re-verified on replay): PASS.
  `.meta` sidecar kept out of `_CACHE_EXTENSIONS`; offline replay re-hashes and
  re-validates (`github.py:510-554`). Residual LOW (cache-owner can rewrite both
  bytes and sidecar) unchanged and accepted.
- GH-SEC-5 (CSV shape/numeric validation): PASS. stdlib `csv.DictReader`, named
  missing-column errors, non-negative `num_pushers`, `quarter` in 1..4, plausible
  `year`, `ParseError`-wrapped rows, UTF-8 guard (`github.py:904-974`). No SQL
  injection: `upsert_observations` stays parameterized.

### Prior LOW follow-ups now resolved

- GH-SEC-6: RESOLVED. `_is_transient` (`http.py:22-30`) retries only
  `_TransientUpstreamError` (429/5xx) and `httpx.TransportError`; 401/403/404, refused
  redirects and oversized bodies fail fast. Proven by
  `test_http.py::test_get_json_does_not_retry_client_errors` (401/403/404 -> 1 call),
  `test_get_json_retries_429_then_succeeds`, `test_get_capped_bytes_does_not_retry_redirect`.
- GH-SEC-9: RESOLVED. `metadata_json` now carries `requested_since`/`requested_until`
  plus `commit_sha`, `csv_sha256`, `requests_made` (`github.py:499-503`); asserted by
  `test_github_innovation_graph.py:99-111`.

### GH-SEC-8 Octoverse (landed in subtask 07)

PASS. `_fetch_octoverse` reads the repo-committed `providers/data/github_octoverse.csv`
via `read_bytes()` with no network (`github.py:427-453`); `_parse_octoverse` reuses the
GH-SEC-5 hardening (stdlib csv, named missing-column errors, positive `rank`, plausible
`year`, known `OctoverseBasis`, `ParseError`-wrapped rows, UTF-8 guard) at
`github.py:977-1046`. The `octoverse-chart` source is refused with `ProviderError`
before any resolution (`github.py:413-417`).

### Fixtures, secrets, live gating

- Fixtures contain no token or user content: `innovation_graph_languages.csv` holds only
  aggregate integer pusher counts + language/`iso2_code`; `octoverse.csv` holds published
  ranks. Golden JSON is normalized output only.
- Secret scan of the diff: no real credentials. The only token-shaped strings are
  synthetic unit-test values (`_FAKE_TOKEN = "ghp_SEKRET..."` and `ghp_liveTOKEN...` scrub
  inputs) used to assert redaction/non-persistence, not live secrets. Token is read only
  from `os.environ`; no hard-coded credential.
- Live test `tests/integration/test_github_live.py` is marked `pytest.mark.live`; the
  `tests/conftest.py` collection hook skips every `live`-keyworded item unless
  `LANGRANK_LIVE_TESTS=1`, so plain `uv run pytest`/CI never reaches the network.

### New finding

### [INFO] GH-SEC-10 Dead unhardened `get_bytes` remains a latent trap
- Vector / evidence: `HttpClientFactory.get_bytes` (`util/http.py:138-153`) still builds
  its client with `follow_redirects=True`, applies no `allowed_host` pin and no size cap.
  It has zero callers in `src/` or `tests/` (grep confirmed); the raw CSV correctly uses
  the hardened `get_capped_bytes`.
- Impact: none today (unreachable). If a future caller wired it to a download it would
  reintroduce the original GH-SEC-3 exposure (cross-host redirect / unbounded body;
  CWE-601, CWE-400).
- Mitigation (non-blocking follow-up): remove `get_bytes`, or route it through the
  hardened capped/pinned/no-redirect path. Hand to `python-expert`.

### Task-close verdict: CLEAR (PASS)

No CRITICAL or HIGH finding. All HIGH/MEDIUM mitigations confirmed with no regression;
the two prior LOW follow-ups (GH-SEC-6, GH-SEC-9) are resolved and tested; Octoverse CSV
ingestion is safe and offline; fixtures are secret-free; the live test is gated. One
INFO-level dead-code cleanup (GH-SEC-10) is the only residual. The Task 02.0 diff clears
the merge gate.
