from __future__ import annotations

from pathlib import Path

from langrank.config import resolve_config


def test_config_precedence(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[langrank]\ndb_path = "file.db"\ncache_path = "cache-dir"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("LANGRANK_DB", str(tmp_path / "env.db"))
    config = resolve_config(
        cli_db=tmp_path / "cli.db",
        cli_cache=tmp_path / "cli-cache",
        cli_config=config_path,
    )
    assert config.db_path == tmp_path / "cli.db"
    assert config.cache_path == tmp_path / "cli-cache"
