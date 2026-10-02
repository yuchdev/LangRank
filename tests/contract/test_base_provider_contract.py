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
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from langrank.errors import ParseError
from langrank.models import FetchRequest, Granularity, RawArtifact
from langrank.providers.base import BaseRatingProvider, FetchPayload, RatingProvider
from langrank.providers.github import GitHubSource
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


@pytest.mark.usefixtures("_no_network")
@pytest.mark.parametrize("provider_id", ["github", "stackoverflow-tags"])
def test_upstream_probe_preserves_pending_pipeline(registry: ProviderRegistry, provider_id: str) -> None:
    """An offline status probe must not change a pending parse/normalize operation."""
    provider = registry.get(provider_id)
    fixtures = Path(__file__).parents[1] / "fixtures"
    if provider_id == "github":
        provider._source = GitHubSource.INNOVATION_GRAPH
        provider._commit_sha = "054c7dbc527518fa2ecfd316efe2aa01f3986c39"
        payload = FetchPayload(None, (fixtures / "github/innovation_graph_languages.csv").read_bytes())
        before = provider.parse(payload)
        state = (provider._source, provider._commit_sha)
        provider.upstream_latest_period()
        assert (provider._source, provider._commit_sha) == state
        assert provider.parse(payload) == before
    else:
        content = (fixtures / "stackoverflow-tags/api_sample.json").read_bytes()
        artifact = RawArtifact(
            id="fixture",
            rating_id=provider_id,
            url="https://example.test",
            retrieved_at=datetime(2024, 4, 1, tzinfo=UTC),
            sha256="fixture",
            mime_type="application/json",
            local_path="unused",
        )
        records = provider.parse(FetchPayload(artifact, content))
        before = provider.normalize(records)
        provider._cache_dir.mkdir(parents=True)
        (provider._cache_dir / f"{provider_id}-fixture.json").write_bytes(content)
        assert provider.upstream_latest_period() == "2024-03"
        assert provider.normalize(records) == before


@pytest.mark.usefixtures("_no_network")
@pytest.mark.parametrize(
    ("provider_id", "expected"),
    [
        ("demo", "2026"),
        ("tiobe", "2025-12"),
        ("pypl", "2025-12"),
        ("redmonk", "2025-06"),
        ("stackoverflow-survey", "2025"),
    ],
)
def test_corrupt_bootstrap_cache_falls_back_to_bundle(
    registry: ProviderRegistry,
    provider_id: str,
    expected: str,
) -> None:
    """Malformed source cells become ParseError and do not abort the status probe."""
    provider = registry.get(provider_id)
    if provider_id == "demo":
        corrupt = b"{broken"
    else:
        lines = provider._bundled_snapshot_payload().content.decode().splitlines()
        cells = lines[1].split(",")
        cells[0] = "invalid"
        lines[1] = ",".join(cells)
        corrupt = "\n".join(lines).encode()
    provider._cache_dir.mkdir(parents=True)
    (provider._cache_dir / f"{provider_id}-corrupt.bin").write_bytes(corrupt)
    with pytest.raises(ParseError):
        provider.parse(FetchPayload(None, corrupt))
    assert provider.upstream_latest_period() == expected


@pytest.mark.usefixtures("_no_network")
@pytest.mark.parametrize(
    ("provider_id", "variant"),
    [(pid, None) for pid in ["tiobe", "pypl", "redmonk", "stackoverflow-survey", "ieee-spectrum", "jetbrains"]]
    + [("github", "octoverse"), ("github", "innovation-graph")],
)
def test_normalization_uses_payload_acquisition_time(
    registry: ProviderRegistry,
    provider_id: str,
    variant: str | None,
) -> None:
    """Every production parse path carries artifact acquisition time into observations."""
    provider = registry.get(provider_id)
    if variant == "innovation-graph":
        provider._source = GitHubSource.INNOVATION_GRAPH
        provider._commit_sha = "054c7dbc527518fa2ecfd316efe2aa01f3986c39"
        content = (Path(__file__).parents[1] / "fixtures/github/innovation_graph_languages.csv").read_bytes()
        payload = FetchPayload(
            RawArtifact(
                "fixture",
                provider_id,
                "https://example.test",
                datetime(2024, 1, 1, tzinfo=UTC),
                "fixture",
                "text/csv",
                "unused",
            ),
            content,
        )
    else:
        payload = provider.fetch(FetchRequest(source=variant))
    assert payload.artifact is not None
    acquired = datetime(2024, 4, 1, tzinfo=UTC)
    payload = replace(payload, artifact=replace(payload.artifact, retrieved_at=acquired))
    provider._retrieved_at = datetime(2020, 1, 1, tzinfo=UTC)
    observations = provider.normalize(provider.parse(payload))
    assert observations
    assert {o.retrieved_at for o in observations} == {acquired}
