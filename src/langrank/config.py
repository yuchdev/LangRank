from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    cache_path: Path
    config_path: Path


def _xdg_path(env_name: str, default_suffix: str) -> Path:
    base = os.environ.get(env_name)
    if base:
        return Path(base) / default_suffix
    return Path.home() / default_suffix


def default_config_path() -> Path:
    return _xdg_path("XDG_CONFIG_HOME", ".config") / "langrank" / "config.toml"


def default_db_path() -> Path:
    return _xdg_path("XDG_DATA_HOME", ".local/share") / "langrank" / "langrank.sqlite"


def default_cache_path() -> Path:
    return _xdg_path("XDG_CACHE_HOME", ".cache") / "langrank"


def load_file_config(config_path: Path) -> dict[str, str]:
    if not config_path.exists():
        return {}
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    section = data.get("langrank", {})
    return {key: str(value) for key, value in section.items()}


def resolve_config(
    *,
    cli_db: Path | None = None,
    cli_cache: Path | None = None,
    cli_config: Path | None = None,
) -> AppConfig:
    config_path = cli_config or default_config_path()
    file_config = load_file_config(config_path)
    env_db = os.environ.get("LANGRANK_DB")
    env_cache = os.environ.get("LANGRANK_CACHE")

    db_path = Path(cli_db or env_db or file_config.get("db_path") or default_db_path())
    cache_path = Path(
        cli_cache or env_cache or file_config.get("cache_path") or default_cache_path()
    )
    return AppConfig(
        db_path=db_path.expanduser(), cache_path=cache_path.expanduser(), config_path=config_path
    )
