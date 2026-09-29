from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Optional

import pytest

from langrank.errors import ParseError
from langrank.models import (
    FetchRequest,
    Granularity,
    MetricDefinition,
    Observation,
    ProviderMetadata,
    SourceRecord,
    ValidationReport,
)
from langrank.providers.base import BaseRatingProvider, FetchPayload, RatingProvider


def _record(period_start: date, *, metric_id: str = "sample-metric") -> SourceRecord:
    """Build a minimal source record anchored at ``period_start`` for tests."""
    return SourceRecord(
        rating_id="sample",
        metric_id=metric_id,
        language="Python",
        period_start=period_start,
        period_end=period_start,
        period_label=period_start.isoformat(),
        granularity=Granularity.MONTH,
        rank=1,
        value=1.0,
        unit="rank",
        source_url="https://example.test",
    )


class _SampleProvider(BaseRatingProvider):
    """Concrete provider used to exercise :class:`BaseRatingProvider` behaviour.

    The payload is a JSON list of ISO ``period_start`` strings; :meth:`parse` turns
    each into a :class:`SourceRecord`. ``native_granularity`` and the bundled
    snapshot are injectable so the tests can drive period formatting and the
    cache/bundle fallback independently.
    """

    provider_id = "sample"

    def __init__(
        self,
        cache_dir: Path,
        *,
        granularity: Granularity = Granularity.MONTH,
        bundled: Optional[FetchPayload] = None,
        raise_on_parse: bool = False,
    ) -> None:
        super().__init__(cache_dir)
        self._granularity = granularity
        self._bundled = bundled
        self._raise_on_parse = raise_on_parse

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="Sample",
            description="Sample provider for base-class tests.",
            homepage=None,
            default_metric="sample-metric",
            native_granularity=self._granularity,
            caveats=[],
            parser_version="sample-v1",
            metrics=[
                MetricDefinition(
                    id="sample-metric",
                    rating_id=self.provider_id,
                    display_name="Sample metric",
                    unit="rank",
                    higher_is_better=False,
                    description="Sample metric.",
                )
            ],
        )

    def fetch(self, request: FetchRequest) -> FetchPayload:
        self._stash_request_window(request)
        return FetchPayload(artifact=None, content=b"[]")

    def parse(self, raw: FetchPayload) -> list[SourceRecord]:
        if self._raise_on_parse:
            raise ParseError("sample parse failure")
        try:
            starts = json.loads(raw.content.decode("utf-8"))
        except ValueError as exc:
            raise ParseError("sample payload is not JSON") from exc
        records = [_record(date.fromisoformat(value)) for value in starts]
        return self._filter_window(records)

    def normalize(self, records: Sequence[SourceRecord]) -> list[Observation]:
        return []

    def validate(self, observations: Sequence[Observation]) -> ValidationReport:
        return ValidationReport()

    def _bundled_snapshot_payload(self) -> Optional[FetchPayload]:
        return self._bundled


def _bundled(starts: list[str]) -> FetchPayload:
    """Build a bundled payload from a list of ISO ``period_start`` strings."""
    return FetchPayload(artifact=None, content=json.dumps(starts).encode("utf-8"))


def test_init_sets_shared_state(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    assert provider._cache_dir == tmp_path / "sample"
    assert provider.last_unmapped == []
    assert provider._request_since is None
    assert provider._request_until is None
    assert provider._request_years is None


def test_stash_request_window_records_bounds(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    request = FetchRequest(since=date(2020, 1, 1), until=date(2024, 1, 1), years=3)
    provider._stash_request_window(request)
    assert provider._request_since == date(2020, 1, 1)
    assert provider._request_until == date(2024, 1, 1)
    assert provider._request_years == 3


def test_filter_window_applies_stashed_bounds(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    provider._stash_request_window(FetchRequest(since=date(2022, 1, 1), until=date(2022, 12, 1)))
    records = [_record(date(2021, 6, 1)), _record(date(2022, 6, 1)), _record(date(2023, 6, 1))]
    filtered = provider._filter_window(records)
    assert [record.period_start for record in filtered] == [date(2022, 6, 1)]


def test_filter_window_empty_returns_empty(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    assert provider._filter_window([]) == []


def test_record_unmapped_dedups_preserving_order(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    provider._record_unmapped("Zig")
    provider._record_unmapped("Nim")
    provider._record_unmapped("Zig")
    assert provider.last_unmapped == ["Zig", "Nim"]


def test_upstream_latest_period_from_cache(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    provider._cache_dir.mkdir(parents=True)
    (provider._cache_dir / "sample-abc123456789.json").write_bytes(
        json.dumps(["2024-03-01", "2025-06-01"]).encode("utf-8")
    )
    assert provider.upstream_latest_period() == "2025-06"


def test_upstream_latest_period_falls_back_to_bundled(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path, bundled=_bundled(["2023-01-01", "2024-11-01"]))
    assert provider.upstream_latest_period() == "2024-11"


def _write_cache(provider: _SampleProvider, content: bytes) -> None:
    """Drop ``content`` into the provider's cache as its newest artifact."""
    provider._cache_dir.mkdir(parents=True)
    (provider._cache_dir / "sample-abc123456789.json").write_bytes(content)


def test_upstream_latest_period_prefers_cache_over_bundled(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path, bundled=_bundled(["2030-01-01"]))
    _write_cache(provider, json.dumps(["2025-06-01"]).encode("utf-8"))
    assert provider.upstream_latest_period() == "2025-06"


def test_upstream_latest_period_unparseable_cache_falls_back_to_bundled(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path, bundled=_bundled(["2024-11-01"]))
    _write_cache(provider, b"not json")
    assert provider.upstream_latest_period() == "2024-11"


def test_upstream_latest_period_empty_cache_falls_back_to_bundled(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path, bundled=_bundled(["2024-11-01"]))
    _write_cache(provider, b"[]")
    assert provider.upstream_latest_period() == "2024-11"


def test_upstream_latest_period_none_when_cache_unparseable_and_no_bundled(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    _write_cache(provider, b"not json")
    assert provider.upstream_latest_period() is None


def test_upstream_latest_period_year_granularity(tmp_path: Path) -> None:
    provider = _SampleProvider(
        tmp_path,
        granularity=Granularity.YEAR,
        bundled=_bundled(["2020-01-01", "2025-01-01"]),
    )
    assert provider.upstream_latest_period() == "2025"


def test_upstream_latest_period_none_when_no_local_artifact(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    assert provider.upstream_latest_period() is None


def test_upstream_latest_period_none_on_parse_error(tmp_path: Path) -> None:
    provider = _SampleProvider(
        tmp_path,
        bundled=_bundled(["2024-01-01"]),
        raise_on_parse=True,
    )
    assert provider.upstream_latest_period() is None


def test_upstream_latest_period_none_when_bundled_empty(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path, bundled=_bundled([]))
    assert provider.upstream_latest_period() is None


def test_base_provider_cannot_instantiate_abstract() -> None:
    with pytest.raises(TypeError):
        BaseRatingProvider(Path("."))  # type: ignore[abstract]


def test_sample_provider_satisfies_rating_provider(tmp_path: Path) -> None:
    provider = _SampleProvider(tmp_path)
    assert isinstance(provider, RatingProvider)
