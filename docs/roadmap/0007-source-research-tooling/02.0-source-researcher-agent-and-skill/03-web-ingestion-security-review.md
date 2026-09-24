# Subtask 02.0/03 - Web-ingestion Security Review

**Task:** [02.0 - Source Researcher Agent & Skill](/docs/roadmap/0007-source-research-tooling/02.0-source-researcher-agent-and-skill/README.md) ·
**Role:** Security Auditor · **Depends on:** 01, 02 · **Status:** ⬜ Not started

## Goal

Threat-model the source-researcher path, where untrusted web content is written into repo
docs by an agent that has `Bash`. Record the verdict in `docs/security/`.

## Baseline

- `security-auditor` produces threat models in `docs/security/` using its STRIDE-lite method.
- `docs/security/README.md` indexes them.
- The `secret_scan.py` PreToolUse hook blocks secret-looking writes, and `guard_bash.py`
  guards Bash commands.

## Files

| Action | Path                                              | Purpose |
|--------|---------------------------------------------------|---------|
| Create | `docs/security/source-researcher-threat-model.md` | Threat model and verdict |
| Modify | `docs/security/README.md`                         | Index entry |
| Modify | `.claude/agents/source-researcher.md`             | Only if findings require an instruction change; the security-auditor recommends, and the Architect applies |

## Symbols / fields

The threat model must cover these threats, each with a mitigation and a residual-risk
rating:

| Threat                                   | Surface                                            |
|------------------------------------------|----------------------------------------------------|
| Prompt injection from fetched pages      | WebFetch/playwright output → agent instructions    |
| Write-scope escape                       | `Write`/`Edit` outside `docs/source-notes`, `docs/research` |
| Command injection                        | `Bash` with note paths/argument text interpolated  |
| Malicious links persisted into docs      | `## Sources` URLs, `homepage`, `terms_url`         |
| Terms/robots violation                   | Crawling depth, bot-check bypass through playwright |
| Data poisoning                           | Fabricated facts presented as cited               |
| Secret leakage                           | Tokens pasted from pages or env into notes         |

## Behaviour & validators

1. Verdict: `PASS`, `PASS WITH NOTES`, or `BLOCK`. Any CRITICAL finding means `BLOCK` for
   Task 02.0 until it is fixed.
2. Each mitigation points at an enforcing mechanism: an agent-instruction line, the skill's
   scope check (subtask 02 step 4), the validator's `url_scheme` rule, or an existing hook.

## Tests

None (review document).

## Success criteria

- [ ] `docs/security/source-researcher-threat-model.md` covers all 7 threats and states a verdict.
- [ ] There are no open CRITICAL findings.
- [ ] `python3 scripts/check_doc_links.py docs/security` exits 0.

## Constraints

- The security-auditor never edits product code (per its agent definition).

## Out of scope

- The MCP server threat model: [Task 03.0/07](/docs/roadmap/0007-source-research-tooling/03.0-read-only-mcp-server/07-threat-model.md).
