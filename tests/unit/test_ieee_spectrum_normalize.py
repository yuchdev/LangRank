from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from langrank.errors import ParseError
from langrank.models import FetchRequest, Granularity
from langrank.providers.base import FetchPayload
from langrank.providers.ieee_spectrum import (
    DATA_PATH,
    RANK_DERIVATION_METHOD,
    IeeeProfile,
    IeeeSpectrumProvider,
    rank_metric_id,
    score_metric_id,
)

#: A minimal well-formed curated CSV: two 2025 spectrum rows (one with an empty
#: score), one 2025 jobs row, and one untracked ``Visual Basic`` label. The header
#: matches the bundled dataset exactly.
_HEADER = "year,profile,rank,language,score,source_url,published_at,methodology_version"
_URL = "https://spectrum.ieee.org/top-programming-languages-2025"
_CSV = (
    f"{_HEADER}\n"
    f"2025,spectrum,1,Python,1,{_URL},2025-09-23,ieee-2025-manual-7metrics\n"
    f"2025,spectrum,2,Java,0.5,{_URL},2025-09-23,ieee-2025-manual-7metrics\n"
    f"2025,jobs,1,SQL,0.9,{_URL},2025-09-23,ieee-2025-manual-7metrics\n"
    f"2025,spectrum,3,Visual Basic,0.1,{_URL},2025-09-23,ieee-2025-manual-7metrics\n"
).encode("utf-8")


def _provider(tmp_path: Path) -> IeeeSpectrumProvider:
    """Build a provider rooted at a throwaway cache dir (no network, no database)."""
    return IeeeSpectrumProvider(tmp_path)


def _payload(content: bytes) -> FetchPayload:
    """Wrap raw CSV bytes as an artifact-less payload, as ``langrank import`` does."""
    return FetchPayload(artifact=None, content=content)


def test_ieee_parse_emits_rank_and_score_per_profile(tmp_path: Path) -> None:
    """Each mapped row yields a rank and a score record on its profile's metric pair."""
    provider = _provider(tmp_path)

    records = provider.parse(_payload(_CSV))

    metric_ids = {record.metric_id for record in records}
    assert rank_metric_id(IeeeProfile.SPECTRUM) in metric_ids
    assert score_metric_id(IeeeProfile.SPECTRUM) in metric_ids
    assert rank_metric_id(IeeeProfile.JOBS) in metric_ids
    assert score_metric_id(IeeeProfile.JOBS) in metric_ids
    # Profiles never collapse into one metric: the jobs SQL row stays on jobs metrics.
    sql_records = [r for r in records if r.language == "SQL"]
    assert {r.metric_id for r in sql_records} == {
        rank_metric_id(IeeeProfile.JOBS),
        score_metric_id(IeeeProfile.JOBS),
    }
    first = records[0]
    assert first.granularity is Granularity.YEAR
    assert first.period_start == date(2025, 1, 1)
    assert first.period_end == date(2025, 12, 31)
    assert first.period_label == "2025"


def test_ieee_normalize_rank_derived_score_raw(tmp_path: Path) -> None:
    """Ranks are derived (competition ranking); scores are raw with their scale."""
    provider = _provider(tmp_path)

    observations = provider.normalize(provider.parse(_payload(_CSV)))

    ranks = [o for o in observations if o.metric_id.endswith("-rank")]
    scores = [o for o in observations if o.metric_id.endswith("-score")]
    assert ranks and scores
    assert all(o.is_derived and o.derivation_method == RANK_DERIVATION_METHOD for o in ranks)
    assert all(not o.is_derived and o.derivation_method is None for o in scores)
    python_score = next(o for o in scores if o.language_id == "python")
    assert python_score.value == 1.0
    assert python_score.metadata_json["score_scale"] == "0-1"


def test_ieee_missing_score_not_fabricated(tmp_path: Path) -> None:
    """An empty score cell yields no score record; the rank is still stored."""
    provider = _provider(tmp_path)
    csv_bytes = (f"{_HEADER}\n2025,spectrum,1,Python,,{_URL},2025-09-23,ieee-2025-manual-7metrics\n").encode("utf-8")

    records = provider.parse(_payload(csv_bytes))

    assert [r.metric_id for r in records] == [rank_metric_id(IeeeProfile.SPECTRUM)]
    observations = provider.normalize(records)
    assert [o.metric_id for o in observations] == [rank_metric_id(IeeeProfile.SPECTRUM)]
    assert observations[0].value == 1.0


def test_ieee_untracked_label_skipped_silently(tmp_path: Path) -> None:
    """``Visual Basic`` is untracked: no observation and no unmapped warning."""
    provider = _provider(tmp_path)

    observations = provider.normalize(provider.parse(_payload(_CSV)))

    assert all(o.language_id != "vb.net" for o in observations)
    assert provider.last_unmapped == []


def test_ieee_unmapped_label_recorded(tmp_path: Path) -> None:
    """A label that resolves to nothing is skipped and recorded in ``last_unmapped``."""
    provider = _provider(tmp_path)
    csv_bytes = (f"{_HEADER}\n2025,spectrum,1,Nonesuchlang,0.3,{_URL},2025-09-23,ieee-2025-manual-7metrics\n").encode(
        "utf-8"
    )

    observations = provider.normalize(provider.parse(_payload(csv_bytes)))

    assert observations == []
    assert provider.last_unmapped == ["Nonesuchlang"]


def test_ieee_unknown_profile_raises(tmp_path: Path) -> None:
    """An unknown profile is rejected rather than dropped or guessed."""
    provider = _provider(tmp_path)
    csv_bytes = (f"{_HEADER}\n2025,mystery,1,Python,1,{_URL},2025-09-23,ieee-2025-manual-7metrics\n").encode("utf-8")

    with pytest.raises(ParseError):
        provider.parse(_payload(csv_bytes))


def test_ieee_missing_column_raises(tmp_path: Path) -> None:
    """A header that drops a required column raises ParseError (import guard)."""
    provider = _provider(tmp_path)
    csv_bytes = (
        "year,profile,rank,language,source_url,published_at,methodology_version\n"
        f"2025,spectrum,1,Python,{_URL},2025-09-23,ieee-2025-manual-7metrics\n"
    ).encode("utf-8")

    with pytest.raises(ParseError):
        provider.parse(_payload(csv_bytes))


def test_ieee_non_utf8_raises(tmp_path: Path) -> None:
    """Non-UTF-8 bytes raise ParseError; a UTF-8 BOM is tolerated."""
    provider = _provider(tmp_path)
    latin1 = f"{_HEADER}\n2025,spectrum,1,Naïve,0.3,{_URL},2025-09-23,v\n".encode("latin-1")

    with pytest.raises(ParseError):
        provider.parse(_payload(latin1))

    bom = b"\xef\xbb\xbf" + (
        f"{_HEADER}\n2025,spectrum,1,Python,1,{_URL},2025-09-23,ieee-2025-manual-7metrics\n".encode()
    )
    assert provider.parse(_payload(bom))  # BOM tolerated, one mapped row parses.


def test_ieee_provenance_fields(tmp_path: Path) -> None:
    """source_document_id names edition+profile; published_at and methodology carry."""
    provider = _provider(tmp_path)

    observations = provider.normalize(provider.parse(_payload(_CSV)))

    python_rank = next(o for o in observations if o.language_id == "python" and o.metric_id.endswith("-rank"))
    assert python_rank.source_document_id == "ieee-tpl-2025-spectrum"
    assert python_rank.source_published_at == datetime(2025, 9, 23, tzinfo=UTC)
    assert python_rank.metadata_json["methodology_version"] == "ieee-2025-manual-7metrics"
    assert python_rank.metadata_json["profile"] == "spectrum"
    assert python_rank.source_url == _URL
    assert python_rank.parser_version == "ieee-spectrum-v1"


def test_ieee_bundled_csv_normalizes_with_no_unmapped(tmp_path: Path) -> None:
    """The whole bundled dataset round-trips fetch->parse->normalize with no unmapped."""
    provider = _provider(tmp_path)
    payload = provider.fetch(FetchRequest())

    observations = provider.normalize(provider.parse(payload))

    assert provider.last_unmapped == []
    # Every profile keeps its own rank/score metric pair, never merged.
    rank_metrics = {o.metric_id for o in observations if o.metric_id.endswith("-rank")}
    assert rank_metrics == {rank_metric_id(profile) for profile in IeeeProfile}
    # Ranks derived, scores raw, across the real dataset.
    assert all(
        o.is_derived and o.derivation_method == RANK_DERIVATION_METHOD
        for o in observations
        if o.metric_id.endswith("-rank")
    )
    assert all(not o.is_derived for o in observations if o.metric_id.endswith("-score"))
    assert payload.content == DATA_PATH.read_bytes()


def test_ieee_score_for_unscaled_edition_raises(tmp_path: Path) -> None:
    content = (
        b"year,profile,rank,language,score,source_url,published_at,methodology_version\n"
        b"2021,spectrum,1,Python,100,https://spectrum.ieee.org/x,2021-08-24,ieee-2019-11metrics-8sources\n"
    )
    with pytest.raises(ParseError, match="no recorded score scale"):
        IeeeSpectrumProvider(tmp_path).parse(FetchPayload(artifact=None, content=content))
