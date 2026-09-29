"""Registry-driven contract tests shared by every provider.

These assert the invariants the OOP refactoring (05.0) promised for *every*
registered provider, exercising the real :class:`ProviderRegistry` instances
rather than a hand-rolled sample provider (that is already covered by
``tests/unit/test_base_provider.py``). The suite iterates whatever the registry
exposes instead of hardcoding a count, but separately pins the expected set of
provider ids so a dropped or renamed provider fails loudly here.
"""

from __future__ import annotations

import re
import socket
import tempfile
from pathlib import Path

import pytest

from langrank.models import Granularity
from langrank.providers.base import BaseRatingProvider, RatingProvider
from langrank.providers.registry import ProviderRegistry

#: The providers milestone 0001 registers; pinned so a dropped/renamed provider
#: is caught even though the per-provider tests below iterate the live registry.
EXPECTED_PROVIDER_IDS = frozenset(
    {
        "demo",
        "tiobe",
        "pypl",
        "redmonk",
        "stackoverflow-survey",
        "stackoverflow-tags",
        "github",
        "ieee-spectrum",
        "jetbrains",
    }
)

_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _registry_provider_ids() -> list[str]:
    """Enumerate the live registry's provider ids (construction does no I/O)."""
    with tempfile.TemporaryDirectory() as tmp:
        registry = ProviderRegistry(Path(tmp))
        return sorted(provider.provider_id for provider in registry.all())


#: Collected once so every provider gets its own parametrized test id.
_PROVIDER_IDS = _registry_provider_ids()


@pytest.fixture()
def registry(tmp_path: Path) -> ProviderRegistry:
    """A registry whose per-provider cache dirs are guaranteed empty."""
    return ProviderRegistry(tmp_path / "cache")


@pytest.fixture()
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any outbound socket attempt fail loudly for offline assertions."""

    def _fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted during offline contract test")

    monkeypatch.setattr(socket.socket, "connect", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)


def test_registry_exposes_expected_provider_ids() -> None:
    assert set(_PROVIDER_IDS) == EXPECTED_PROVIDER_IDS
    assert len(_PROVIDER_IDS) == len(EXPECTED_PROVIDER_IDS)


def test_registry_provider_ids_are_unique() -> None:
    assert len(_PROVIDER_IDS) == len(set(_PROVIDER_IDS))


@pytest.mark.parametrize("provider_id", _PROVIDER_IDS)
def test_provider_is_base_and_protocol_instance(registry: ProviderRegistry, provider_id: str) -> None:
    provider = registry.get(provider_id)
    assert isinstance(provider, BaseRatingProvider)
    assert isinstance(provider, RatingProvider)


@pytest.mark.parametrize("provider_id", _PROVIDER_IDS)
def test_metadata_provider_id_matches_registry_key(registry: ProviderRegistry, provider_id: str) -> None:
    provider = registry.get(provider_id)
    assert provider.metadata().provider_id == provider_id


@pytest.mark.parametrize("provider_id", _PROVIDER_IDS)
def test_cache_dir_is_scoped_to_provider(registry: ProviderRegistry, provider_id: str) -> None:
    provider = registry.get(provider_id)
    assert provider._cache_dir.name == provider_id


@pytest.mark.parametrize("provider_id", _PROVIDER_IDS)
def test_last_unmapped_starts_empty(registry: ProviderRegistry, provider_id: str) -> None:
    provider = registry.get(provider_id)
    assert provider.last_unmapped == []


@pytest.mark.usefixtures("_no_network")
@pytest.mark.parametrize("provider_id", _PROVIDER_IDS)
def test_upstream_latest_period_offline_matches_granularity(registry: ProviderRegistry, provider_id: str) -> None:
    provider = registry.get(provider_id)
    # An untouched registry cache must not exist yet, so any period returned
    # comes from a repo-bundled snapshot, never the network or a stray cache.
    assert not provider._cache_dir.exists()

    period = provider.upstream_latest_period()

    if period is None:
        return
    granularity = provider.metadata().native_granularity
    pattern = _YEAR_RE if granularity is Granularity.YEAR else _MONTH_RE
    assert pattern.match(period) is not None, (provider_id, granularity, period)
