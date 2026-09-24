# Subtask 02.0/05 - Plugin Trust Model & Security Review

**Task:** [02.0 - External Provider Plugin Loading](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md) ·
**Role:** Security Auditor · **Depends on:** 02 (reviews 03 before merge) · **Status:** ⬜ Not started

## Goal

Produce a threat model for plugin loading and a merge verdict for subtasks 02-03. Plugins run
arbitrary Python in the `langrank` process with the user's privileges and write into the same
SQLite DB (via `FetchService`); the document states that plainly, defines what the loader does
and does **not** protect against, and lists required mitigations.

## Baseline

- [docs/security/README.md](/docs/security/README.md) - threat-model location/convention.
- Loader design in [02.0 README § Design notes](/docs/roadmap/0006-provider-extensibility/02.0-external-provider-plugins/README.md#design-notes).
- Observations from plugins are persisted by core with `rating_id` = plugin ID - a plugin could
  emit rows claiming another `rating_id` unless `FetchService` checks.

## Files

| Action | Path                                           | Purpose |
|--------|------------------------------------------------|---------|
| Create | `docs/security/threat-model-provider-plugins.md` | STRIDE-style threat model + verdict |
| Modify | `docs/security/README.md`                      | Index entry |
| Modify | `src/langrank/services/fetch.py` *(if finding confirmed; implemented by Python Expert)* | Reject observations whose `rating_id` ≠ `provider.provider_id` |
| Create | `tests/unit/test_fetch_rating_id_guard.py` *(same condition)* | Guard test |

## Symbols / fields

| Symbol                                  | Kind   | Type / signature | Default | Notes |
|-----------------------------------------|--------|------------------|---------|-------|
| `ValidationReport` code `foreign_rating_id` | code | `Severity.ERROR` | - | Added by `FetchService` when a provider emits another rating's rows |

## Behaviour & validators

The threat model must cover, each with likelihood/impact and mitigation-or-accepted-risk:

1. **Arbitrary code execution at import** - accepted risk; mitigation = explicit trust statement
   ("installing a plugin = trusting its author like any Python dependency"), `--no-plugins`,
   `doctor` visibility of every loaded distribution.
2. **Entry-point squatting / name collision** with built-ins - mitigated by built-in-wins and
   duplicate-skip rules (subtask 03).
3. **Data integrity** - plugin writing rows for another rating (`foreign_rating_id` guard),
   unflagged derived values, missing provenance (contract helper, not enforceable at runtime).
4. **Cache path traversal** - plugin-supplied IDs used in paths (`cache_dir/"plugins"/<name>`):
   entry-point name must match `^[a-z0-9][a-z0-9-]{0,63}$` or be skipped.
5. **Network / source-terms** - plugins with default network access fall under the
   [Milestone 0001 legal gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate); core cannot enforce, guide requires declaration.
6. **Secrets** - plugins reading env/credentials: out of core's control; documented.
7. Decision on an allowlist (`plugins_allow`) - required or not, with rationale.

## Tests

| Test function                                  | File                                    | Type | Asserts |
|------------------------------------------------|-----------------------------------------|------|---------|
| `test_fetch_rejects_foreign_rating_id`         | `tests/unit/test_fetch_rating_id_guard.py` | Mock | Stub provider emitting `rating_id="tiobe"` under ID `acme` → report error `foreign_rating_id`, nothing upserted |
| `test_invalid_plugin_name_skipped`             | `tests/unit/test_plugin_discovery.py`   | Mock | Entry point `../evil` skipped (`invalid_name` reason) |

## Success criteria

- [ ] Threat model committed with a verdict (no CRITICAL open findings) before 02.0/03 merges.
- [ ] Each required mitigation has an owning subtask or test.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Security Auditor writes docs only; code changes for confirmed findings go to Python Expert
  (per the loop roster: `security-auditor` then `python-expert`).

## Out of scope

- Process sandboxing / subprocess isolation of plugins (explicitly rejected as premature infrastructure unless the review finds it mandatory).
