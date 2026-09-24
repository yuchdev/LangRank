# Subtask 05.0/01 - Edition Calendar Script

**Task:** [05.0 - Source Watch Loop](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/README.md) ·
**Role:** Python Expert · **Depends on:** Task 01.0 · **Status:** ⬜ Not started

## Goal

Add `scripts/source_calendar.py`. It computes which source notes are due for a check on a
given date and prints deterministic JSON. When a DB path is given, it also includes the
latest local period for each existing provider.

## Baseline

- `scripts/check_source_notes.py:load_notes()` / `SourceNote` (Task 01.0/02).
- The DB schema has `observations.period_start`. `SELECT MAX(period_start) … WHERE rating_id = ?`
  mirrors `Database.latest_observation_for_provider`. The script opens the DB read-only with
  `file:…?mode=ro` and stays stdlib-only, so it does not import `langrank`.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Create | `scripts/source_calendar.py`                 | Calendar logic + CLI |
| Create | `tests/scripts/test_source_calendar.py`      | Tests |
| Create | `tests/fixtures/source-notes/calendar/*.md`  | Notes covering each cadence |

## Symbols / fields

| Symbol               | Kind      | Type / signature                                                                  | Default | Notes |
|----------------------|-----------|-----------------------------------------------------------------------------------|---------|-------|
| `CADENCE_MAX_AGE_DAYS` | constant | `dict[str, int]`                                                                 | `monthly: 45, quarterly: 110, semiannual: 200, annual: 400, irregular: 400` | Overdue threshold after `last_verified` |
| `DueSource`          | dataclass | frozen; `source_id`, `provider_id`, `reason: Literal["publication-window", "overdue", "never-verified"]`, `window: tuple[str, str] \| None`, `last_verified`, `latest_local_period: str \| None` | - | |
| `due_sources()`      | function  | `(notes: Sequence[SourceNote], *, today: date, window_days: int = 21, latest_local: Mapping[str, str] \| None = None) -> list[DueSource]` | - | Pure |
| `read_latest_local()`| function  | `(db_path: Path) -> dict[str, str]`                                               | - | Read-only URI |
| `main()`             | function  | `(argv: list[str] \| None = None) -> int`                                         | - | `--today YYYY-MM-DD`, `--db PATH`, `--window-days N`, `--json` (default) |

## Behaviour & validators

1. Only `status` ∈ {`existing`, `planned`, `candidate`} are considered. `rejected`/`defunct`
   are skipped.
2. `publication-window`: `today` falls within `window_days` after the 1st of any month in
   `typical_publication_month`, and `last_verified` is before that month's 1st.
3. `overdue`: `today - last_verified > CADENCE_MAX_AGE_DAYS[cadence]`. `cadence: none` is
   never overdue.
4. `monthly` cadence (`typical_publication_month: null`) is due when `last_verified` falls
   in an earlier calendar month than `today`.
5. Output is sorted by `source_id`, as JSON with `sort_keys=True` and a trailing newline.
6. The script is read-only: it never writes notes or the DB.

## Tests

| Test function                                 | File                                     | Type        | Asserts |
|-----------------------------------------------|------------------------------------------|-------------|---------|
| `test_publication_window_selects_annual`      | `tests/scripts/test_source_calendar.py`  | Unit        | July 10 + `[7]` + last_verified June → due |
| `test_publication_window_respects_verified`   | same                                     | Unit        | Same, but last_verified July 5 → not due |
| `test_semiannual_two_windows`                 | same                                     | Unit        | `[1, 6]` due in both windows |
| `test_monthly_due_next_month`                 | same                                     | Unit        | |
| `test_overdue_threshold_per_cadence`          | same (parametrized)                      | Unit        | Boundary ±1 day |
| `test_rejected_and_defunct_skipped`           | same                                     | Unit        | |
| `test_latest_local_from_read_only_db`         | same                                     | Integration | tmp DB with demo rows → mapping; file unchanged |
| `test_json_output_deterministic`              | same                                     | Unit        | Two runs byte-identical |

## Success criteria

- [ ] All tests pass. The script is stdlib-only.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No network access. `today` is injectable, and no test depends on the wall clock.

## Out of scope

- Web checks: [subtask 02](/docs/roadmap/0007-source-research-tooling/05.0-source-watch-loop/02-source-watch-loop-definition.md).
