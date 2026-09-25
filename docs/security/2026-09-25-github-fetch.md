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
