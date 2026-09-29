# 0007 - Config Resolution: CLI Flag > Env Var > TOML File > XDG Default (stdlib only)

> **Status:** Accepted
>
> **Date:** 2026-09-29 _(recorded retroactively; in force since the core scaffold, `6d57d06`)_
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

LangRank has very little configuration: where the SQLite database lives (`db_path`), where
raw artifacts are cached (`cache_path`), and where to find an optional config file. Provider
secrets (e.g. `LANGRANK_STACKEXCHANGE_KEY`, `GITHUB_TOKEN`) are read by the providers that
need them and are deliberately not part of this file-backed config.

The same paths must be settable in several ways: a one-off flag during an experiment, an
environment variable in CI or tests (pointing at a temp dir), and a persistent file for a
user's daily setup - with a sensible default when nothing is set, following platform
conventions rather than dumping files into the working directory.

## Decision

`resolve_config()` in `src/langrank/config.py` resolves each path independently, the highest
precedence first:

1. **CLI flag** (`--db`, `--cache`, `--config` on the root Typer callback);
2. **Environment variable** (`LANGRANK_DB`, `LANGRANK_CACHE`);
3. **TOML file**, `[langrank]` table keys `db_path` / `cache_path`, read with stdlib
   `tomllib` from `--config` or `$XDG_CONFIG_HOME/langrank/config.toml`
   (default `~/.config/langrank/config.toml`); a missing file is not an error;
4. **XDG default** - `$XDG_DATA_HOME/langrank/langrank.sqlite` and
   `$XDG_CACHE_HOME/langrank` (falling back to `~/.local/share` and `~/.cache`).

Paths are `expanduser()`-ed and returned as a frozen `AppConfig`. `main_callback` builds it
once per invocation into `AppState`; nothing else reads the environment for these paths.

## Alternatives Considered

| Alternative                                                       | Pros                                                               | Cons                                                                                     | Reason rejected                                              |
|-------------------------------------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| `pydantic-settings` / Dynaconf layered config                     | Typed validation; many source types                                | New dependency for two path values; precedence rules become library behaviour to learn   | Rejected - disproportionate for the current config surface   |
| Env vars only                                                     | Simplest; twelve-factor friendly                                   | No persistent per-user setup without shell profile edits                                 | Rejected - a CLI tool used daily benefits from a config file |
| Files in the current working directory (`./langrank.sqlite`)      | Obvious location                                                   | Different DB per directory the user happens to run from; clutters repos                  | Rejected - XDG locations give one stable default             |
| Hand-written four-level precedence with stdlib `tomllib` (chosen) | Zero dependencies; explicit, testable in one function; follows XDG | Values are strings/paths without schema validation; each new setting needs manual wiring | **Accepted**                                                 |

## Consequences

### Positive

- Tests isolate themselves by setting `LANGRANK_DB` / `LANGRANK_CACHE` or passing flags,
  without touching the user's real database.
- No dependency beyond the standard library; precedence is readable in ten lines.
- Platform-conventional locations out of the box.

### Negative

- No schema validation: an unknown key in `[langrank]` is silently ignored, and all values
  are coerced to `str`.
- If configuration grows (per-provider options, rate limits, plugin paths in milestone
  0006), this hand-rolled approach should be revisited in a superseding ADR rather than
  extended ad hoc.

## Validation / Rollout

- `tests/unit/test_config.py` covers the precedence chain (`test_config_precedence`) and
  the home-directory fallback when XDG variables are unset.
- Documented in [/CLAUDE.md](/CLAUDE.md) (CLI section) and the CLI help.

## Links

- **Roadmap task:** _(none - part of the core scaffold, `6d57d06`)_
- **Supporting specs:** `src/langrank/config.py`
- **Related ADRs:** [0003](/docs/adr/0003-sqlite-storage-and-natural-key-upsert.md), [0006](/docs/adr/0006-source-acquisition-policy.md)
