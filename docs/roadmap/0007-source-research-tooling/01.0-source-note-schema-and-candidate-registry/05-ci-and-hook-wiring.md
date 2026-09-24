# Subtask 01.0/05 - CI & Hook Wiring

**Task:** [01.0 - Source Note Schema & Candidate Registry](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/README.md) ·
**Role:** Python Expert · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Make source-note validity and registry freshness automatic gates. CI runs them as a hard
gate. A PostToolUse hook runs them as a non-blocking reminder when a note is edited.

## Baseline

- `.github/workflows/ci.yml` runs `uv run ruff check .`, `ruff format --check`, `mypy src`
  and `pytest` on 3.12/3.13.
- `.claude/settings.json` PostToolUse `Write|Edit|MultiEdit` already chains
  `post_edit_format.py`, `style_fixes.py`, `dep_audit.py` and `doc_link_check.py`.
- `.claude/hooks/_common.py` provides `read_event`, `edited_path`, `allow` and
  `append_log`.

## Files

| Action | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| Modify | `.github/workflows/ci.yml`            | Add step `- run: python scripts/check_source_notes.py --check --check-registry` after pytest |
| Create | `.claude/hooks/source_note_check.py`  | PostToolUse hook: when the edited path is under `docs/source-notes/`, validate that note and re-check the registry |
| Modify | `.claude/settings.json`               | Register the hook after `doc_link_check.py` |
| Modify | `docs/agent/hooks.md`                 | Document the new hook |

## Symbols / fields

| Symbol       | Kind     | Type / signature        | Default | Notes |
|--------------|----------|-------------------------|---------|-------|
| `main()`     | function | `() -> int` in hook     | -       | Always returns 0 (non-blocking); prints problems as a reminder |

## Behaviour & validators

1. The hook is a no-op (it exits 0 silently) for paths outside `docs/source-notes/`.
2. The hook imports `scripts/check_source_notes.py` through `importlib.util.spec_from_file_location`.
   It does not shell out.
3. On a stale registry, the hook prints the exact command to fix it:
   `python scripts/check_source_notes.py --write-registry`. It never rewrites files itself.
4. The hook logs one line per run to `.claude/logs/source-note-check.log` through
   `append_log`, following the `doc-link-check.log` convention.

## Tests

| Test function                               | File                                        | Type | Asserts |
|---------------------------------------------|---------------------------------------------|------|---------|
| `test_hook_ignores_unrelated_paths`         | `tests/scripts/test_source_note_hook.py`    | Unit | Event for `src/x.py` → exit 0, no output |
| `test_hook_reports_invalid_note_nonblocking`| same                                        | Unit | Event for an invalid fixture note → exit 0, problem text printed |

## Success criteria

- [ ] CI has the new step, and a deliberately broken note fails CI locally with `act` or an
      equivalent dry run (manual check, recorded in the PR).
- [ ] The hook is registered in `.claude/settings.json` and documented in `docs/agent/hooks.md`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Hooks must never block a session. That matches the `doc_link_check` contract.

## Out of scope

- Link checking of notes, which the existing `doc_link_check` hook already covers.
