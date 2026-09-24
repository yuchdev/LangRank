# Subtask 03.0/01 - Retention Policy Config

**Task:** [03.0 - Source Archival Strategy](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Add the `RetentionPolicy` enum, a provider-declared default, and config resolution with the
documented precedence.

## Baseline

- `config.py:AppConfig(db_path, cache_path, config_path)`; `load_file_config` flattens the
  `[langrank]` table to `dict[str, str]`; env vars `LANGRANK_DB`, `LANGRANK_CACHE`.
- `cli.py:main_callback` exposes `--db`, `--cache`, `--config`.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/models.py` | `RetentionPolicy`; `ProviderMetadata.default_retention` |
| Modify | `src/langrank/config.py` | `AppConfig.retention`, `AppConfig.retention_overrides`, `resolve_retention()` |
| Modify | `src/langrank/cli.py` | global `--retention` option on `main_callback` |
| Modify | `src/langrank/providers/stackoverflow_survey.py` | `default_retention=RetentionPolicy.YEARLY` |
| Modify | `tests/unit/test_config.py` | Precedence tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `RetentionPolicy` | StrEnum | `ALL="all"`, `LATEST="latest"`, `YEARLY="yearly"`, `NONE="none"` | - | |
| `ProviderMetadata.default_retention` | field | `RetentionPolicy \| None` | `None` | |
| `AppConfig.retention` | field | `RetentionPolicy \| None` | `None` | Global from CLI/env/TOML; `None` = not set |
| `AppConfig.retention_source` | field | `str` | `"default"` | `"cli"`, `"env"`, `"file"`, `"default"` |
| `AppConfig.retention_overrides` | field | `dict[str, RetentionPolicy]` | `{}` | TOML `[langrank.retention]` table |
| `resolve_config` | function | new kw `cli_retention: str \| None = None` | - | |
| `resolve_retention` | function | `(config: AppConfig, metadata: ProviderMetadata) -> tuple[RetentionPolicy, str]` | - | Returns policy + source label |
| `LANGRANK_RETENTION` | env var | `str` | - | |

## Behaviour & validators

1. Precedence in `resolve_retention`: CLI > env > TOML per-provider override > TOML global
   `retention` > `metadata.default_retention` > `RetentionPolicy.LATEST`. The per-provider
   TOML override beats the TOML global but **not** CLI/env (explicit invocation wins).
2. Invalid values anywhere → `ConfigurationError` naming the source and allowed values.
3. `load_file_config` keeps flattening only scalar keys (nested tables skipped) so the
   existing `dict[str, str]` contract holds; overrides parsed by
   `load_retention_overrides(config_path)`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_retention_defaults_to_latest` | `tests/unit/test_config.py` | Unit | no config → `LATEST`, source `"default"` |
| `test_retention_provider_default_used_when_unset` | same | Unit | survey → `YEARLY` |
| `test_retention_precedence_cli_env_file` | same | Unit | full precedence matrix |
| `test_retention_toml_override_beats_toml_global` | same | Unit | |
| `test_retention_invalid_value_raises` | same | Unit | `ConfigurationError` |
| `test_load_file_config_ignores_nested_tables` | same | Unit | existing contract preserved |

## Success criteria

- [ ] Every policy value parseable from CLI, env, and TOML.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Keep `resolve_config` backwards-compatible (new kwargs optional).

## Out of scope

- Applying the policy - [04](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/04-archival-service.md).
