from __future__ import annotations

import os
from pathlib import Path

import pytest

from langrank.config import AppConfig
from langrank.db import Database

os.environ.setdefault("MPLBACKEND", "Agg")


@pytest.fixture(autouse=True)
def _set_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPLBACKEND", "Agg")


@pytest.fixture()
def app_paths(tmp_path: Path) -> AppConfig:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[langrank]\n", encoding="utf-8")
    return AppConfig(
        db_path=tmp_path / "langrank.sqlite",
        cache_path=tmp_path / "cache",
        config_path=config_path,
    )


@pytest.fixture()
def database(app_paths: AppConfig) -> Database:
    return Database(app_paths.db_path)
