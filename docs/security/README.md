# Security

Threat models, security review outputs, and posture documentation for Language Ranking.

The `security-auditor` agent owns this directory. Every change touching auth,
secrets, external integrations, or untrusted-input ingestion triggers a security
review whose output is stored here.

## Naming convention

`threat-model-<scope>.md` for threat models, `review-<scope>-<YYYY-MM-DD>.md`
for point-in-time reviews.

## What a threat model must contain

1. **Scope** - which components and trust boundaries are in scope.
2. **Assets** - what secrets, PII, and data are handled.
3. **Threat actors** - attacker profiles considered.
4. **STRIDE analysis** - Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation.
5. **Mitigations** - existing controls and open gaps.
6. **Verdict** - CRITICAL (merge blocked) / HIGH / MEDIUM / LOW / INFO.

## Security rules (non-negotiable)

- Never log secrets; rely on this project's log-redaction mechanism (if any)
  and verify it covers new sinks.
- Never hard-code credentials. Read from settings/env.
- Treat all untrusted external input as sensitive - no unredacted raw input
  in logs, exceptions, stored reports, or API error bodies.
- Untrusted input must never reach a shell, SQL string, `eval`, or an AI
  prompt without sanitization/parameterization.

## Draft threat model - `langrank` ingestion and storage

> **SME REVIEW NEEDED (AI-drafted - verify before relying on this):**
>
> **1. Scope.** The whole application is one locally installed CLI (`langrank.cli:main`) with no
> server, no API, no authentication, and no multi-user surface. Trust boundaries: (a) third-party
> source artifacts entering `provider.fetch()`; (b) arbitrary local files entering
> `cli.py::import_data` via `langrank import --rating <id> <path>`; (c) the on-disk cache under
> `cache_path` re-read on later runs; (d) user configuration - the TOML file read by
> `config.py::load_file_config` and the `LANGRANK_DB`/`LANGRANK_CACHE` env vars, both of which
> become filesystem paths; (e) the local SQLite database. Out of scope: network transport, since
> `util/http.py::HttpClientFactory` is defined but no provider calls it yet - all four production
> providers currently read bundled snapshots from `src/langrank/providers/data/*.csv`. **Re-scope
> this document the moment a provider is wired to the network.**
>
> **2. Assets.** No credentials, no PII, no money. What is actually worth protecting: the
> **integrity and provenance of observations** (the product itself), the cached raw artifacts
> (third-party, possibly copyrighted - `docs/roadmap/0001-generic-implementation/plan.md` §21/§22),
> the user's SQLite DB at `~/.local/share/langrank/langrank.sqlite`, and absolute home-directory
> paths stored in `raw_artifacts.local_path` and echoed by `doctor`/`status` (these carry the OS
> username). Survey `sample_size`/`population` are aggregate methodology metadata, not PII.
>
> **3. Threat actors.** A compromised or hostile upstream source (or an MITM once fetching goes
> live); a user importing an untrusted CSV from a third party; a co-located local process able to
> write the cache dir or the config file. There is no remote attacker path today.
>
> **4. STRIDE (draft).**
> - *Spoofing* - a substituted upstream artifact is indistinguishable from the real one: sha256 is
>   computed over whatever arrived (`providers/common.py::payload_from_content`), so it detects
>   change, not authenticity. No signature or pinning exists. **Gap.**
> - *Tampering* - the highest-impact risk. Doctored input yields wrong-but-plausible ranks that
>   flow through `normalize()` into `observations` and out to charts and CSVs. Partial control:
>   each provider's `validate()` enforces positive ranks, 0..100 percentages, and duplicate
>   detection, and `FetchService` skips the upsert when the report is not `ok`. **Gap:** the
>   `import` command bypasses `FetchService` entirely, records no `RawArtifact`, and creates no
>   `fetch_runs` row when validation fails - a rejected import leaves no audit trail.
> - *Repudiation* - `fetch_runs` plus the per-`Observation` provenance chain
>   (`source_document_id`, `retrieved_at`, `parser_version`, `raw_record_hash`) give a good trail;
>   the `import` path is the hole above.
> - *Information disclosure* - low. The main leak is home-directory paths and full source URLs in
>   the DB, exports, and uncaught tracebacks.
> - *Denial of service* - self-inflicted rather than adversarial: `parse()` decodes the entire
>   artifact into memory, `query_rows` has no `LIMIT`, and `upsert_observations` issues two
>   statements per observation. An oversized import is a memory/time hazard with no size cap.
> - *Elevation of privilege* - no privilege boundary exists. Note that `LANGRANK_DB`/`LANGRANK_CACHE`
>   and the `import` path argument are unvalidated write/read targets in the user's own context.
>
> **5. Mitigations - present.** All SQL values are `?`-bound (`db/repository.py` concatenates
> fragments but never interpolates data); no `eval`, no `shell=True`, no subprocess anywhere;
> providers are barred from touching SQL; `PRAGMA foreign_keys = ON`; frozen dataclasses; strict-ish
> `mypy` on `src`. **Mitigations - open gaps.** No size or MIME limit on ingested content; malformed
> CSV surfaces as a raw `KeyError`/`ValueError`/`UnicodeDecodeError` rather than a `LangRankError`;
> no artifact authenticity check; no cache-poisoning defense (cached files are re-read and trusted);
> `import` bypasses artifact recording; §22's source-policy review (API availability, robots policy,
> terms of use, request rate, redistribution rights) is not yet recorded for any source.
>
> **6. Verdict (draft).** MEDIUM overall for the current offline shape - the realistic damage is
> silently corrupted data rather than compromise. Re-assess to **HIGH** and require a full review
> before merging the first provider that actually fetches over the network, ingests a survey ZIP,
> or authenticates to a source.
