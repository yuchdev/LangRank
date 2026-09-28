from __future__ import annotations

import os
from pathlib import Path

import pytest

from langrank.config import AppConfig
from langrank.db import Database

os.environ.setdefault("MPLBACKEND", "Agg")

#: Env var opting a run into the ``live`` network tests.
_LIVE_TESTS_ENV = "LANGRANK_LIVE_TESTS"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``live`` tests unless the opt-in env var is set to ``1``.

    ``live`` tests perform real outbound network requests, so plain
    ``uv run pytest`` (used by CI, which sets no marker filter) must never run
    them. They execute only when ``LANGRANK_LIVE_TESTS=1``.

    :param config: The active pytest config (unused).
    :param items: Collected test items, mutated in place to add skip markers.
    """
    if os.environ.get(_LIVE_TESTS_ENV) == "1":
        return
    skip_live = pytest.mark.skip(reason=f"live network test; set {_LIVE_TESTS_ENV}=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


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
