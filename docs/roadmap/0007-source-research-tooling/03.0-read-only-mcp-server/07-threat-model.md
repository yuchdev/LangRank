# Subtask 03.0/07 - MCP Server Threat Model

**Task:** [03.0 - Read-only LangRank MCP Server](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/README.md) ·
**Role:** Security Auditor · **Depends on:** 04, 05 · **Status:** ⬜ Not started

## Goal

Threat-model the MCP server as a new external integration surface and issue a verdict.
CRITICAL findings block the task.

## Baseline

- The `security-auditor` STRIDE-lite method; outputs go to `docs/security/`.
- The server is local, stdio-only, and read-only (subtasks 02-05).

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `docs/security/mcp-server-threat-model.md`   | Threat model + verdict |
| Modify | `docs/security/README.md`                    | Index entry |

## Symbols / fields

Threats that must be covered:

| Threat                            | Surface / check |
|-----------------------------------|-----------------|
| DB tampering through the server   | `mode=ro` URI; no write methods imported (grep evidence) |
| SQL injection                     | All params bound; no f-string SQL in `query_observations` |
| Path traversal                    | `langrank://source-notes/{source_id}` regex + `is_relative_to` |
| DoS / oversized responses         | `limit` ≤ 5000, `languages` ≤ 50 |
| Information disclosure            | Error messages carry no absolute paths beyond the configured DB path, and no tracebacks |
| Prompt injection *out* to clients | Source-note Markdown and `source_url`s returned verbatim: document that clients must treat them as untrusted |
| Supply chain                      | `mcp>=2.2,<3` extra: `/dep-audit` result attached |
| Transport exposure                | stdio only; no HTTP listener |

## Behaviour & validators

1. Verdict: `PASS`, `PASS WITH NOTES`, or `BLOCK`.
2. Each mitigation cites the test from subtask 06 that proves it, where one exists.

## Tests

None (review).

## Success criteria

- [ ] The threat model covers all 8 threats, states a verdict, and has no open CRITICAL findings.
- [ ] `python3 scripts/check_doc_links.py docs/security` exits 0.

## Constraints

- Read and docs-write only. Findings go to `python-expert` for fixes.

## Out of scope

- The researcher agent's web ingestion: [Task 02.0/03](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/03-web-ingestion-security-review.md).
