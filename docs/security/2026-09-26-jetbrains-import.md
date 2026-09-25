# Threat Model - jetbrains raw-data import - 2026-09-26

Scope: the `raw-data` acquisition mode of the JetBrains provider (Task 04.0), i.e.
`langrank import --rating jetbrains <raw.csv>` over JetBrains' anonymized *State of Developer
Ecosystem* response dump. Specs:
[04.0/01 source note & gate](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/01-source-note-and-policy-gate.md),
[04.0/06 raw-data import](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/06-raw-data-import.md).
Gate context / verified facts: [source note](/docs/source-notes/jetbrains.md).
Reviewer: Security Auditor agent.

This model sets forward requirements (JB-SEC-n) that subtask 06 MUST meet before the `raw-data`
mode clears the merge gate. The `published` mode (bundled curated CSV, 0 network) is out of scope
here and is cleared manual-only by the source note.

## Assets & trust boundaries

- Assets: the operator's local machine memory/disk; the local cache dir (`LANGRANK_CACHE`); the
  SQLite DB and any exports derived from it; the repo working tree (must never receive a raw file);
  the licence obligations attached to the raw data (CC BY-NC-SA 4.0 for 2024/2025).
- Trust boundary: a **large (verified 87-98 MB zipped; hundreds of MB uncompressed), untrusted,
  user-supplied file** crosses into `import` -> `provider.parse` -> `normalize` -> `validate` ->
  `Database.upsert_observations`. The file is anonymized by JetBrains but contains **500+ columns**
  including free-text answers.
- Adversary model: primarily a **malformed/oversized/hostile file** (a corrupted download, a
  tampered dump, or a decompression bomb), not a remote network attacker - `import` makes no network
  request. Impact is local DoS, privacy leakage into the DB/exports, and licence violation, not RCE.
- Current weakness (pre-existing): `cli.py:import_data` builds
  `FetchPayload(content=path.read_bytes())` (`src/langrank/cli.py:359`) - it reads the **entire**
  file into memory before parsing.

## Findings

### [HIGH] JB-SEC-1 Whole-file read into memory - unbounded-memory DoS
- Vector / evidence: `cli.py:import_data` calls `path.read_bytes()` (`src/langrank/cli.py:359`) on a
  file the source note confirms is hundreds of MB uncompressed; the provider then parses the in-memory
  bytes. A large or padded file exhausts RAM before any validation runs (CWE-400, CWE-789).
- Impact: local out-of-memory / process kill on a legitimate 90 MB+ dump, worse on a crafted file.
- Mitigation: for the jetbrains import path, stream - parse with `csv.reader` over a text wrapper of
  the file object (or `io.BytesIO`) and count in **one pass without building per-row objects**
  (spec 06); enforce an explicit **byte-size cap** and a **max-row cap**, rejecting oversized input
  with a clear `ParseError`/`FetchError` before ingesting. Do not route this path through
  `path.read_bytes()`.

### [HIGH] JB-SEC-2 Zip handling (zip-slip / zip-bomb) if a `.zip` is accepted
- Vector / evidence: the distribution artifact is `RawData.zip` (verified 87-98 MB). Spec 06 defines
  import over `<raw.csv>` (already-extracted), but an operator may point `import` at the zip. Naive
  extraction enables path traversal via crafted member names (`../`, absolute paths - zip-slip,
  CWE-22) and decompression amplification (zip-bomb, CWE-409) that dwarfs the on-disk size.
- Impact: files written outside the intended dir; disk/memory exhaustion.
- Mitigation: **require a pre-extracted CSV** for this subtask and reject non-CSV input with a clear
  error (simplest safe default). If zip support is later added, never extract by attacker-controlled
  name; read only the single expected member via `zipfile` streaming with a **per-member and total
  uncompressed-size cap**, reject members whose name is absolute or contains `..`, and reject
  archives with unexpected/multiple members.

### [HIGH] JB-SEC-3 CSV parsing robustness on untrusted input
- Vector / evidence: 500+ columns, multi-select (delimited) answer cells, arbitrary/huge field
  contents, inconsistent row widths, non-UTF-8/BOM/embedded-NUL bytes. Python's default
  `csv.field_size_limit` is very large, so a single pathological field can still amplify memory
  (CWE-1284, CWE-400); malformed rows can raise unhandled exceptions (CWE-20).
- Mitigation: set an explicit `csv.field_size_limit`; decode UTF-8 (with BOM handling) and raise
  `ParseError` on decode failure; wrap per-row `ValueError`/`KeyError`/`csv.Error` in `ParseError`;
  skip/flag malformed rows deterministically rather than aborting the whole import silently; parse
  multi-select columns by splitting on the documented delimiter only. Never `eval`. DB writes stay
  parameterized (`upsert_observations` uses `?`), so no SQL injection (CWE-89 N/A).

### [HIGH] JB-SEC-4 PII / free-text answers must never be stored
- Vector / evidence: the dump is anonymized but includes **free-text** answer columns that can carry
  incidental identifying detail. Storing any response-level or free-text value would move
  potentially-identifying data into the DB and every downstream export (CWE-359, privacy).
- Impact: privacy exposure; ingest of data JetBrains released only in aggregate spirit.
- Mitigation: the parser reads **only** the specific language-question columns named by the
  `QUESTION_REGISTRY` for the detected year; every other column (especially free-text) is ignored and
  never persisted. Store **only aggregate counts / shares and the denominator** - never a
  response-level row, never a free-text string. Add a test asserting free-text columns produce no
  stored value.

### [HIGH] JB-SEC-5 No raw file committed/cached-beyond-local; licence propagation
- Vector / evidence: raw 2024/2025 data is **CC BY-NC-SA 4.0** (NonCommercial + ShareAlike +
  Attribution); 2022/2023 is attribution-only. Committing a raw file, redistributing it, or copying it
  into a shared/published cache would violate the licence and (for the large zips) bloat the repo.
- Impact: licence/legal violation; leakage of the licensed corpus.
- Mitigation: never write the raw file (zip or CSV) into the repo working tree or any shared cache;
  it stays in the operator's **local** cache dir only. Test fixtures must be **tiny synthetic** rows,
  never verbatim JetBrains data. The derived `-raw` series must carry the source licence
  (`CC-BY-NC-SA-4.0` / attribution string) and attribution into release metadata
  ([0004 Task 02.0](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md)).

### [MEDIUM] JB-SEC-6 Derived-vs-published integrity (no silent conflation)
- Vector / evidence: LangRank's unweighted shares differ from JetBrains' published weighted numbers;
  presenting them as equivalent misleads (integrity/repudiation, CWE-345).
- Mitigation: `is_derived=True`, `derivation_method="unweighted_respondent_share"`, metric IDs with a
  `-raw` suffix that **never share a series** with `published`; record the denominator, detected
  survey year, and per-year question wording in `metadata_json`; a `MethodologyNote` when wording
  changes. Enforce distinct metric IDs with a test (spec 06 success criterion).

### [MEDIUM] JB-SEC-7 No automated download / SSRF from the import path
- Vector / evidence: `import` must read a **local** operator-supplied file and make **no** network
  request; auto-fetching the raw zip would add SSRF/large-download-amplification surface and conflict
  with the manual-only gate and the Google-Drive/CDN terms.
- Mitigation: keep `import` network-free (reads a local path only). If a future auto-download is ever
  added it must reuse the hardened `get_capped_bytes` path (HTTPS + `allowed_host` pin,
  `follow_redirects=False`, byte cap) and never live in this subtask.

### [LOW] JB-SEC-8 CSV-formula injection is an export-time concern
- Vector / evidence: a language label beginning `=`/`+`/`-`/`@` only matters if a stored value is
  later opened in a spreadsheet via `export csv`; only alias-mapped languages are persisted and SQL
  is parameterized (CWE-1236).
- Mitigation: rely on alias-only persistence here; leave formula-neutralizing to the export path.
  No action in subtask 06.

### [LOW] JB-SEC-9 Error/log redaction of raw cell contents
- Vector / evidence: a parse error that echoes a raw cell into an exception or log could surface a
  free-text/PII fragment (CWE-532, CWE-209).
- Mitigation: parse errors reference row/column **indices** and counts, never cell contents; no raw
  cell text in log or exception messages.

## Verdict: PASS_WITH_FOLLOWUP

No CRITICAL finding: `import` is a local, network-free, operator-run path; the raw-data derivation is
not yet implemented, and the design already mandates aggregate-only storage, `-raw` derived metrics,
and local-only caching. But **JB-SEC-1..JB-SEC-5 are HIGH requirements** subtask 06 MUST implement and
prove with tests before the `raw-data` mode merges to `master`: streaming + size/row caps (replacing
the `cli.py:359` whole-file read on this path), CSV robustness (`field_size_limit`, wrapped row
errors, encoding guard), free-text/PII exclusion (registry-column-only reads, aggregate counts only),
and no-redistribution/licence propagation. Hand JB-SEC-1..JB-SEC-5 code changes to `python-expert`
and the regression tests (oversized-input rejection, malformed-CSV, free-text-not-stored,
`-raw`-metric-distinctness, synthetic-fixtures-only) to `testing-expert`; re-audit the subtask-06
implementation before the merge gate clears. Any HIGH left unmet at implementation time escalates to
BLOCK.
</content>

---

## Re-audit - subtask 04.0/06 implementation - 2026-09-26

Re-audited the uncommitted implementation (`git diff HEAD`) against JB-SEC-1..9. Scope:
`jetbrains.py` (`import_path`, `_reject_zip`, `_bounded_csv_field_size`, `_aggregate_raw`,
`_parse_raw`, `_detect_survey_year`, `_records_from_counts`), `jetbrains_questions.py` raw prefixes,
`base.py` `SupportsRawImport`, `cli.py` dispatch, `tests/unit/test_jetbrains_raw.py` (15 tests, all
passing). Product code was not modified.

### Per-requirement verdicts

- **JB-SEC-1 (memory DoS) - PASS_WITH_FOLLOWUP.** `st_size` byte cap (`_MAX_IMPORT_BYTES` 600 MB)
  is checked before any read, a streamed `csv.reader` is capped at `_MAX_IMPORT_ROWS` (2 M) rows, and
  no per-row objects are retained. Residual MEDIUM: `csv.reader` materialises one physical line as a
  single field list; neither `field_size_limit` (bounds per-field *bytes*, 1 MB) nor the row cap
  (counts *rows*) bounds the *number of fields on one line*, so a crafted single ~600 MB line - or the
  header row itself - is read into one list (pointer-per-field amplification over the file). Bounded by
  the byte cap, so not unbounded, but a real spike. Also `st_size` on a FIFO/char-device reports 0 and
  slips past the byte cap (row + field caps still bound it).
- **JB-SEC-2 (zip-slip/zip-bomb) - PASS.** 4-byte `PK` magic check rejects `.zip` on both
  `import_path` (reads only 4 bytes) and `_parse_raw`; a pre-extracted CSV is required. Tested.
- **JB-SEC-3 (CSV robustness) - PASS.** `csv.field_size_limit` set and restored via a try/finally
  context manager (process-global value restored on every exit path that reaches it - the oversize and
  zip rejections return before it is ever set); `utf-8-sig` tolerates BOM; non-UTF-8 raises
  `ParseError`; width mismatch and `csv.Error` are wrapped. Restoration proven on the malformed-field
  path.
- **JB-SEC-4 (PII/free-text) - PASS.** Only the detected year's registry prefix columns are read;
  storage is aggregate counts + denominator only; the free-text-never-stored test passes across
  records, observations and metadata.
- **JB-SEC-5 (no raw committed/cached) - PASS.** No raw dump in the git tree (committed
  `data/jetbrains.csv` is the published curated file); fixtures are tiny synthetic rows; the
  import-never-touches-cache test passes; the session scratchpad holds no raw JetBrains dump (only the
  724-row published curated CSV, no `proglang::` layout, no zip).
- **JB-SEC-6 (derived -raw distinct) - PASS.** `is_derived=True`,
  `derivation_method=unweighted_respondent_share`, `-raw` metric IDs disjoint from `PUBLISHED_METRICS`,
  denominator stored as `metadata['denominator']` and `sample_size`. Tested.
- **JB-SEC-7 (no download/SSRF) - PASS.** `fetch(--source raw-data)` raises `NotImplementedError`;
  import is local-file-only. Tested.
- **JB-SEC-9 (error/log redaction) - PASS.** Parse/width/year errors cite row/column indices and
  counts only; tests assert cell values and the PII fixture never appear in messages.
- **JB-SEC-8 - N/A** for this subtask (export-time concern, unchanged).

### Required fixes

- **MEDIUM** - JB-SEC-1 residual: bound per-line size / field count before full row materialisation
  (e.g. a max-line-bytes guard on the stream, or reject files whose header field count is implausible)
  so a single huge line or hyper-wide row cannot amplify memory up to ~byte-cap x pointer size.
- **LOW** - JB-SEC-1: reject non-regular input (`stat.S_ISREG`) so a FIFO/char-device with
  `st_size == 0` cannot bypass the byte cap.

### Missing tests

- No test for the single-huge-line / hyper-wide-row residual (the exact amplification vector).
- Field-size-limit restoration is tested only on the malformed-field path, not on the
  `UnicodeDecodeError` decode path or the year-detection `ParseError` path.
- No test exercising the `cli.py` dispatch branch itself (asserting a non-`SupportsRawImport`
  provider still takes the `read_bytes()`/`parse()` path).

### Re-audit verdict: CLEAR (PASS_WITH_FOLLOWUP)

No CRITICAL or HIGH remains: JB-SEC-1..5 HIGH requirements are implemented and test-proven. The one
residual (single-line field-count amplification) is MEDIUM and bounded by the byte cap, so it does not
BLOCK the merge gate; track it plus the LOW FIFO edge and the three missing tests as follow-ups. Hand
the two fixes to `python-expert` and the three tests to `testing-expert`.
