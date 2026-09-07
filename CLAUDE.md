# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`langrank` is a Python/Typer CLI that fetches, normalizes, stores, queries, exports, and plots
historical programming-language popularity signals (TIOBE, PYPL, RedMonk, Stack Overflow Survey,
plus a synthetic `demo` provider) into a local SQLite database. See `README.md` for the
methodological warning: different sources measure different things (search visibility vs. tutorial
interest vs. GitHub/SO activity vs. self-reported usage) and must never be silently treated as one
comparable "popularity score."

## Commands

```bash
uv sync                        # install deps (Python >=3.12, managed via uv)

uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run mypy src                # type check (strict-ish: disallow_untyped_defs, src only)
uv run pytest                  # full test suite
uv run pytest tests/unit/test_config.py::test_name  # single test
uv run pytest -m "not integration"  # skip provider-integration-marked tests

uv run langrank fetch all --years 10
uv run langrank query --rating tiobe --language python --years 10
uv run langrank plot --rating redmonk --metric rank --languages python,c++,rust --years 10
uv run langrank export csv --ratings tiobe,pypl --since 2016 --output history.csv
```

CI (`.github/workflows/ci.yml`) runs exactly the four checks above (ruff check, ruff format --check,
mypy, pytest) on Python 3.12 and 3.13 — run them all before considering a change done.

## Architecture

The whole app is one linear pipeline, and almost every feature touches multiple stages of it:

```
provider.fetch()  ->  provider.parse()  ->  provider.normalize()  ->  provider.validate()  ->  Database.upsert_observations()  ->  services (query/export/plot)  ->  CLI (typer commands in cli.py)
```

**Providers** (`src/langrank/providers/`) implement the `RatingProvider` Protocol (`providers/base.py`):
`metadata()`, `fetch(request) -> FetchPayload`, `parse(payload) -> list[SourceRecord]`,
`normalize(records) -> list[Observation]`, `validate(observations) -> ValidationReport`. Providers
**must never write directly to SQLite** — persistence is the caller's (service/CLI) job via
`Database`. `providers/registry.py` is a flat hand-registered dict (`ProviderRegistry`); a new
provider must be added there. `providers/common.py` has shared helpers: `payload_from_content`
(caches raw bytes + computes sha256 for `RawArtifact`), `build_observation`/`build_observation_hash`
(deterministic hash of the raw `SourceRecord`, stored as `raw_record_hash` for change detection).
Use `providers/demo.py` as the reference implementation when adding a new one — it's the offline,
deterministic provider that exists specifically to exercise the architecture without network calls.

**Data model** (`src/langrank/models.py`): frozen dataclasses all the way down. Key distinction —
`SourceRecord` (provider's raw language string, pre-normalization) vs. `Observation` (canonical
`language_id`, provenance fields: `source_document_id`, `is_derived`, `derivation_method`,
`retrieved_at`, `source_published_at`, `parser_version`, `raw_record_hash`). This provenance chain is
the project's core invariant (see `docs/roadmap/0001-generic-implementation/plan.md` #27): every
value must stay traceable to a source, date, metric definition, parser version, acquisition mode,
and normalization rule — don't add code paths that lose that trail.

**Storage** (`src/langrank/db/`): raw `sqlite3` (no ORM). `migrations.py` holds an append-only list
of `(version, sql)` tuples applied in order by `migrate()`, tracked in a `schema_migrations` table —
add a new tuple with the next integer version rather than editing an existing one.
`repository.py`'s `Database` class is the only thing that touches SQL; it owns observation
upsert-by-natural-key (`rating_id, metric_id, language_id, period_start, granularity` — see the
`ON CONFLICT` in `upsert_observations`), language/alias normalization lookups
(`alias_to_language`, case/punctuation-insensitive via `_normalize_alias`), and the validation
queries used by `ValidationService`.

**Normalization** (`src/langrank/normalization/languages.py`): the canonical language list and
source-specific aliases (e.g. PYPL's combined `c-cpp` category) that `Database.seed_languages` loads
on every `Database()` construction. Adding a new provider usually means adding aliases here, not just
a new provider file.

**Services** (`src/langrank/services/`): thin orchestration layer between providers/DB and the CLI —
`FetchService` (runs the pipeline, records `fetch_runs`, never lets validation errors block a
dry-run), `QueryService`, `ValidationService`, `StatusService`. Business logic belongs here, not in
`cli.py`.

**CLI** (`src/langrank/cli.py`): Typer app with subcommand groups (`ratings`, `languages`, `export`).
`AppState` (built once per invocation in `main_callback`) wires up `Database` + `ProviderRegistry`
from `resolve_config()` (`config.py` — precedence is CLI flag > env var (`LANGRANK_DB`,
`LANGRANK_CACHE`) > TOML config file > XDG default path). Errors are raised as `LangRankError`
subclasses (`errors.py`) and caught centrally in `main()`.

## Conventions worth knowing

- Providers are pure functions over their inputs where possible — no hidden network calls outside
  `fetch()`, no DB access. This is what makes `tests/contract/` provider tests fixture-driven.
- Ranks/values are never fabricated or interpolated; missing data stays missing. Don't add fallback
  values for absent observations.
- Derived/normalized values must be explicitly flagged (`is_derived`, `derivation_method`) and never
  presented as if they were raw source data.
- Rating axes are not comparable across providers without explicit normalization (see
  `docs/roadmap/0001-generic-implementation/plan.md` for the planned `rank_percentile` approach) —
  don't build features that plot raw values from different ratings on one shared axis.
- `docs/roadmap/` follows a strict Milestone -> Task -> Subtask hierarchy documented in
  `docs/roadmap/README.md`; when a doc references another doc, use an absolute-from-repo-root link
  (`/docs/...`), not relative `../` chains.
