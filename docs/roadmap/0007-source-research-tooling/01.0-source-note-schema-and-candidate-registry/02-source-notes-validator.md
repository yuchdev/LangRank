# Subtask 01.0/02 - Source-notes Validator Script

**Task:** [01.0 - Source Note Schema & Candidate Registry](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Add `scripts/check_source_notes.py`, a stdlib-only validator that parses each note's
restricted-YAML front matter and enforces the schema from subtask 01. It exposes a reusable
`load_notes()` function for the registry generator (subtask 04), the scaffold (Task 04.0),
and the calendar (Task 05.0).

## Baseline

- `scripts/check_doc_links.py` shows the conventions to follow:
  - `REPO_ROOT`;
  - `argparse`;
  - `--check`;
  - positional paths;
  - exit 1 on findings;
  - a trailing "N file(s) scanned, M problem(s) found." summary.
- `scripts/` has no tests yet. `pyproject.toml` sets `testpaths = ["tests"]`, and mypy
  covers `src` only.

## Files

| Action | Path                                         | Purpose                                      |
|--------|----------------------------------------------|----------------------------------------------|
| Create | `scripts/check_source_notes.py`              | Parser, schema model, validator, CLI         |
| Create | `tests/scripts/__init__.py`                  | Test package                                 |
| Create | `tests/scripts/conftest.py`                  | Load `scripts/*.py` modules through `importlib` (no `sys.path` hacks in tests) |
| Create | `tests/scripts/test_check_source_notes.py`   | Validator tests                              |
| Create | `tests/fixtures/source-notes/valid/*.md`     | ≥ 2 valid notes (one `existing`, one `candidate`) |
| Create | `tests/fixtures/source-notes/invalid/*.md`   | One file per defect class                    |

## Symbols / fields

| Symbol                         | Kind      | Type / signature                                                     | Default | Notes |
|--------------------------------|-----------|----------------------------------------------------------------------|---------|-------|
| `NOTES_DIR`                    | constant  | `Path`                                                               | `REPO_ROOT / "docs/source-notes"` | |
| `SKIP_STEMS`                   | constant  | `frozenset[str]`                                                     | `{"README", "TEMPLATE"}` | |
| `FrontMatterError`             | class     | `Exception` subclass with `line: int`                                | - | |
| `parse_front_matter()`         | function  | `(text: str) -> tuple[dict[str, object], int]`                       | - | Returns fields and the body start line; raises `FrontMatterError` |
| `SourceNote`                   | dataclass | frozen; one attribute per schema field, plus `path: Path`, `body: str` | - | `scores: dict[str, int]`; `typical_publication_month: tuple[int, ...] \| None` |
| `Problem`                      | dataclass | frozen; `path: Path`, `line: int`, `code: str`, `message: str`       | - | `str()` → `path:line: [code] message` |
| `validate_note()`              | function  | `(path: Path, *, today: date) -> tuple[SourceNote \| None, list[Problem]]` | - | |
| `load_notes()`                 | function  | `(notes_dir: Path = NOTES_DIR, *, today: date \| None = None) -> tuple[list[SourceNote], list[Problem]]` | - | Public API for later tasks |
| `main()`                       | function  | `(argv: list[str] \| None = None) -> int`                            | - | `--check` (default), positional paths |

## Behaviour & validators

Each problem `code` is one of:

1. `fm_missing` - the file does not start with a `---` fenced front-matter block.
2. `fm_syntax` - a line is outside the restricted subset. Allowed lines are `key: scalar`,
   `key: [a, b]`, `key: null`, two-space-indented `sub: int` lines under `scores:`, and `#`
   comments. The problem reports the offending line number.
3. `field_missing` / `field_unknown` - a required field is absent, or a key is not in the
   schema.
4. `enum_value` - a value is not in the allowed set for `status`, `measures`, `access[]`,
   `redistribution`, `automation`, `granularity`, `cadence` or `priority`.
5. `id_mismatch` - `source_id` differs from the filename stem.
6. `existing_requires_provider` - `status: existing` with `provider_id: null`.
7. `gate_fields` - `status` ∈ {`existing`, `planned`} with a null `terms_url` or
   `automation: unknown`.
8. `date_format` / `date_future` - a bad `last_verified` or `history_start` value, or a
   `last_verified` later than `today`.
9. `month_range` - an entry of `typical_publication_month` outside 1-12.
10. `scores` - the map lacks one of the 6 rubric keys, has an extra key, or has a value
    outside 1-5.
11. `priority_status` - `rejected`/`defunct` with a priority other than `none`.
12. `roadmap_missing` - `roadmap` is set but the path does not exist under `REPO_ROOT`.
13. `section_missing` - a required body heading is absent or out of order.
14. `url_scheme` - `homepage` or `terms_url` is not `https://`.

Behavior:

- Parsing never executes or evaluates anything. Values are plain strings, ints, or `null`,
  and lists hold only those.
- `today` is injectable for deterministic tests. The CLI uses `date.today()`.

## Tests

| Test function                                   | File                                       | Type | Asserts |
|-------------------------------------------------|--------------------------------------------|------|---------|
| `test_parse_front_matter_supported_subset`      | `tests/scripts/test_check_source_notes.py` | Unit | Scalars, inline lists, null, nested `scores` round-trip |
| `test_parse_front_matter_rejects_block_lists`   | same                                       | Unit | `- item` YAML block list → `FrontMatterError` with line |
| `test_valid_fixtures_have_no_problems`          | same                                       | Unit | Every `valid/*.md` → `[]` |
| `test_each_invalid_fixture_reports_its_code`    | same (parametrized over `invalid/*.md`)    | Unit | Filename `<code>.md` → exactly that code reported |
| `test_template_and_readme_are_skipped`          | same                                       | Unit | `load_notes` ignores `SKIP_STEMS` |
| `test_last_verified_future_uses_injected_today` | same                                       | Unit | `date_future` depends on `today` |
| `test_main_exit_codes`                          | same                                       | Unit | 0 on valid dir, 1 on invalid dir, summary line printed |

## Success criteria

- [ ] All 14 problem codes have an invalid fixture and a passing test.
- [ ] `python scripts/check_source_notes.py tests/fixtures/source-notes/valid` exits 0.
- [ ] The script imports only the standard library (`grep -E "^(import|from) " scripts/check_source_notes.py` shows stdlib modules only).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Stdlib only and Python ≥ 3.12, with full type annotations: the same standard as `src/`,
  even though mypy's `files` is `src`.
- No bare `except:`. Parse errors become `Problem`s; they never produce a traceback.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Registry generation: [subtask 04](/docs/roadmap/0007-source-research-tooling/01.0-source-note-schema-and-candidate-registry/04-candidate-registry-generation.md).
- URL liveness checks. Network access is not allowed in this validator.
